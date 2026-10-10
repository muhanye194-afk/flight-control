from functools import lru_cache
from typing import List

from sentence_transformers import SentenceTransformer

from rag.schemas import DocumentChunk

MODEL_NAME = "BAAI/bge-small-en-v1.5"


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME)


def embed_documents(chunks: List[DocumentChunk]) -> List[List[float]]:
    model = get_embedding_model()
    texts = [chunk.content for chunk in chunks]

    vectors = model.encode(
        texts,
        normalize_embeddings=True
    )

    return vectors.tolist()


def embed_query(query: str) -> List[float]:
    model = get_embedding_model()

    vector = model.encode(
        query,
        normalize_embeddings=True
    )

    return vector.tolist()