from typing import AsyncIterator

from app.llm.llm_client import stream_answer
from app.retrieval.hybrid_search import hybrid_search

SYSTEM_PROMPT = """You are a senior engineer explaining this codebase to a new \
contributor. Answer ONLY using the provided code excerpts. Cite the file path \
and line range for every claim. If the excerpts don't contain the answer, say so \
instead of guessing."""


def _build_context(chunks) -> str:
    parts = []
    for c in chunks:
        parts.append(f"### {c.file_path} (lines {c.start_line}-{c.end_line})\n{c.content}")
    return "\n\n".join(parts)


async def answer_question(client, repo_id: str, question: str) -> AsyncIterator[str]:
    chunks = hybrid_search(client, question, repo_id)
    context = _build_context(chunks)
    prompt = f"Code excerpts:\n{context}\n\nQuestion: {question}"
    async for token in stream_answer(SYSTEM_PROMPT, prompt):
        yield token