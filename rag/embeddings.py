import hashlib
import os
import re
from functools import lru_cache
from typing import Any, List

from rag.schemas import DocumentChunk

MODEL_NAME = "BAAI/bge-small-en-v1.5"
EMBEDDING_BACKEND = os.getenv(
    "FLIGHT_CONTROL_EMBEDDING_BACKEND",
    "sentence-transformer",
)
HASH_VECTOR_SIZE = 384


@lru_cache(maxsize=1)
def get_embedding_model() -> Any:
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(MODEL_NAME)


def hash_embedding(text: str) -> List[float]:
    """Return a deterministic local vector for tests and offline CI."""
    vector = [0.0] * HASH_VECTOR_SIZE
    tokens = re.findall(r"[a-z0-9_]+", text.lower())

    for token in tokens:
        digest = hashlib.blake2b(
            token.encode("utf-8"),
            digest_size=8,
        ).digest()
        bucket = int.from_bytes(digest[:4], "big") % HASH_VECTOR_SIZE
        direction = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[bucket] += direction

    norm = sum(value * value for value in vector) ** 0.5

    if norm:
        vector = [value / norm for value in vector]

    return vector


def embed_documents(chunks: List[DocumentChunk]) -> List[List[float]]:
    texts = [chunk.content for chunk in chunks]

    if EMBEDDING_BACKEND == "hash":
        return [hash_embedding(text) for text in texts]

    model = get_embedding_model()

    vectors = model.encode(
        texts,
        normalize_embeddings=True
    )

    return vectors.tolist()


def embed_query(query: str) -> List[float]:
    if EMBEDDING_BACKEND == "hash":
        return hash_embedding(query)

    model = get_embedding_model()

    vector = model.encode(
        query,
        normalize_embeddings=True
    )

    return vector.tolist()
