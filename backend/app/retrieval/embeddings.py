from functools import lru_cache
from typing import List

from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"  # small, fast, free, runs locally — swap for Voyage AI later if needed


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME)


def embed_texts(texts: List[str]) -> List[List[float]]:
    model = _get_model()
    return model.encode(texts, convert_to_numpy=True).tolist()


def embed_query(text: str) -> List[float]:
    return embed_texts([text])[0]
