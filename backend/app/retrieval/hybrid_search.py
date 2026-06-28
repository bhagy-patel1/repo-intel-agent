from typing import Dict, List

from app.chunking.chunk_models import Chunk
from app.retrieval.bm25_index import get_or_create_index
from app.retrieval.vector_store import semantic_search


def hybrid_search(client, query: str, repo_id: str, top_k: int = 8) -> List[Chunk]:
    """Reciprocal rank fusion of BM25 and semantic results.

    Simple and robust — it only uses rank position, not raw scores, so
    there's no normalization headache from two different scoring scales.
    """
    semantic_hits = semantic_search(client, query, repo_id, top_k=top_k * 2)
    bm25_hits = get_or_create_index(repo_id).search(query, top_k=top_k * 2)

    scores: Dict[str, float] = {}
    chunks_by_id: Dict[str, Chunk] = {}

    for rank, hit in enumerate(semantic_hits):
        chunk = Chunk(**hit.payload)
        scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0) + 1 / (rank + 1)
        chunks_by_id[chunk.chunk_id] = chunk

    for rank, chunk in enumerate(bm25_hits):
        scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0) + 1 / (rank + 1)
        chunks_by_id[chunk.chunk_id] = chunk

    ranked_ids = sorted(scores, key=scores.get, reverse=True)[:top_k]
    return [chunks_by_id[cid] for cid in ranked_ids]
