from dataclasses import dataclass, field
from typing import Dict, List, Optional

from rank_bm25 import BM25Okapi

from app.chunking.chunk_models import Chunk


@dataclass
class BM25Index:
    """In-memory BM25 index, one per repo. Rebuilt on ingestion."""

    chunks: List[Chunk] = field(default_factory=list)
    _bm25: Optional[BM25Okapi] = None

    def build(self, chunks: List[Chunk]) -> None:
        self.chunks = chunks
        tokenized = [c.to_search_text().lower().split() for c in chunks]
        self._bm25 = BM25Okapi(tokenized)

    def search(self, query: str, top_k: int = 10) -> List[Chunk]:
        if not self._bm25:
            return []
        scores = self._bm25.get_scores(query.lower().split())
        ranked = sorted(zip(scores, self.chunks), key=lambda x: x[0], reverse=True)
        return [chunk for _, chunk in ranked[:top_k]]


# repo_id -> index. Swap for Redis/disk persistence once this matters for uptime.
_INDEXES: Dict[str, BM25Index] = {}


def get_or_create_index(repo_id: str) -> BM25Index:
    if repo_id not in _INDEXES:
        _INDEXES[repo_id] = BM25Index()
    return _INDEXES[repo_id]
