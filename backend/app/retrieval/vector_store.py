import os
from typing import List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.chunking.chunk_models import Chunk
from app.retrieval.embeddings import embed_query, embed_texts

COLLECTION = "code_chunks"
VECTOR_SIZE = 384  # matches all-MiniLM-L6-v2


def get_client(url: Optional[str] = None) -> QdrantClient:
    resolved_url = url or os.environ.get("QDRANT_URL", "http://localhost:6333")
    return QdrantClient(url=resolved_url)


def ensure_collection(client: QdrantClient) -> None:
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION not in existing:
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=qmodels.VectorParams(size=VECTOR_SIZE, distance=qmodels.Distance.COSINE),
        )


def upsert_chunks(client: QdrantClient, chunks: List[Chunk]) -> None:
    vectors = embed_texts([c.to_search_text() for c in chunks])
    points = [
        qmodels.PointStruct(id=i, vector=vec, payload=chunk.model_dump())
        for i, (vec, chunk) in enumerate(zip(vectors, chunks))
    ]
    client.upsert(collection_name=COLLECTION, points=points)


def semantic_search(client: QdrantClient, query: str, repo_id: str, top_k: int = 10):
    query_vec = embed_query(query)
    return client.search(
        collection_name=COLLECTION,
        query_vector=query_vec,
        query_filter=qmodels.Filter(
            must=[qmodels.FieldCondition(key="repo_id", match=qmodels.MatchValue(value=repo_id))]
        ),
        limit=top_k,
    )