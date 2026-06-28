import os
from typing import AsyncIterator

from groq import AsyncGroq

MODEL = "llama-3.3-70b-versatile"  # see console.groq.com/docs/models for other options

_client = AsyncGroq(api_key=os.environ["GROQ_API_KEY"])


async def stream_answer(system_prompt: str, user_question: str) -> AsyncIterator[str]:
    stream = await _client.chat.completions.create(
        model=MODEL,
        max_completion_tokens=1024,
        stream=True,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_question},
        ],
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta