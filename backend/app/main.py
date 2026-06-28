from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agents.repo_qa_agent import answer_question
from app.chunking.ast_chunker import chunk_file
from app.graph.import_graph import build_import_graph, summarize_graph
from app.ingestion.github_fetch import clone_repo, walk_source_files
from app.llm.llm_client import stream_answer
from app.retrieval.bm25_index import get_or_create_index
from app.retrieval.vector_store import ensure_collection, get_client, upsert_chunks

app = FastAPI(title="Repo Intelligence Agent")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

qdrant = get_client()
ensure_collection(qdrant)


class IngestRequest(BaseModel):
    repo_url: str
    repo_id: str


class AskRequest(BaseModel):
    repo_id: str
    question: str


class ArchitectureRequest(BaseModel):
    repo_id: str


@app.post("/ingest")
def ingest(req: IngestRequest):
    """Clone, chunk, and index a repo. Run once per repo before /ask."""
    repo_path = clone_repo(req.repo_url, f"data/repos/{req.repo_id}")

    all_chunks = []
    for file_path, content in walk_source_files(repo_path):
        all_chunks.extend(chunk_file(req.repo_id, file_path, content))

    upsert_chunks(qdrant, all_chunks)
    get_or_create_index(req.repo_id).build(all_chunks)

    return {"repo_id": req.repo_id, "chunks_indexed": len(all_chunks)}


@app.post("/ask")
async def ask(req: AskRequest):
    async def event_stream():
        async for token in answer_question(qdrant, req.repo_id, req.question):
            yield token

    return StreamingResponse(event_stream(), media_type="text/plain")


@app.post("/architecture")
async def architecture(req: ArchitectureRequest):
    """Summarize repo structure using the import graph + README. Run after /ingest."""
    repo_path = Path(f"data/repos/{req.repo_id}")
    graph = build_import_graph(repo_path)
    summary = summarize_graph(graph)

    readme = ""
    for name in ("README.md", "readme.md"):
        candidate = repo_path / name
        if candidate.exists():
            readme = candidate.read_text(encoding="utf-8")[:3000]
            break

    prompt = (
        f"README excerpt:\n{readme}\n\n"
        f"Most-imported modules: {summary['most_imported']}\n"
        f"Likely entry points: {summary['likely_entry_points']}\n\n"
        "In 3-4 paragraphs, explain this codebase's architecture: what it does, "
        "the main layers or modules, and where execution likely starts."
    )

    system = (
        "You are explaining a codebase's architecture to a new contributor. "
        "Base your answer only on the README excerpt and the module signals provided. "
        "If those signals are sparse or you can't identify real structure from them, "
        "say so plainly and stick to what the README actually states — do not invent "
        "generic software-architecture filler (presentation layer, business logic layer, "
        "etc.) that isn't grounded in this specific codebase."
    )
    text = "".join([t async for t in stream_answer(system, prompt)])
    return {"architecture_summary": text}