import re
from typing import Dict, List, Optional

import numpy as np
from rank_bm25 import BM25Okapi

from rag.embeddings import embed_documents, embed_query
from rag.ingest import ingest_knowledge_base
from rag.schemas import DocumentChunk, RetrievalResult

RRF_K = 60


def tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9_]+", text.lower())


def make_rank_lookup(order: np.ndarray) -> Dict[int, int]:
    return {
        int(chunk_index): rank
        for rank, chunk_index in enumerate(order, start=1)
    }


class HybridRetriever:
    def __init__(self, chunks: List[DocumentChunk]):
        if not chunks:
            raise ValueError("知识库不能为空")

        self.chunks = chunks

        corpus_tokens = [
            tokenize(f"{chunk.title} {chunk.section} {chunk.content}")
            for chunk in chunks
        ]

        self.bm25 = BM25Okapi(corpus_tokens)

        self.document_vectors = np.asarray(
            embed_documents(chunks),
            dtype=np.float32
        )

    def get_eligible_indices(
        self,
        domain: Optional[str]
    ) -> np.ndarray:
        if domain is None:
            return np.arange(len(self.chunks))

        eligible_indices = [
            index
            for index, chunk in enumerate(self.chunks)
            if chunk.metadata.get("domain") in {
                domain,
                "global"
            }
        ]

        if not eligible_indices:
            return np.arange(len(self.chunks))

        return np.asarray(
            eligible_indices,
            dtype=np.int64
        )

    def search(
        self,
        query: str,
        top_k: int = 4,
        domain: Optional[str] = None
    ) -> List[RetrievalResult]:
        query_tokens = tokenize(query)

        if not query_tokens:
            raise ValueError("查询内容不能为空")

        bm25_scores = self.bm25.get_scores(query_tokens)
        bm25_order = np.argsort(bm25_scores)[::-1]

        query_vector = np.asarray(
            embed_query(query),
            dtype=np.float32
        )

        dense_scores = self.document_vectors @ query_vector
        dense_order = np.argsort(dense_scores)[::-1]

        bm25_ranks = make_rank_lookup(bm25_order)
        dense_ranks = make_rank_lookup(dense_order)

        rrf_scores = np.zeros(
            len(self.chunks),
            dtype=np.float32
        )

        for rank, chunk_index in enumerate(
            bm25_order,
            start=1
        ):
            rrf_scores[chunk_index] += 1 / (
                RRF_K + rank
            )

        for rank, chunk_index in enumerate(
            dense_order,
            start=1
        ):
            rrf_scores[chunk_index] += 1 / (
                RRF_K + rank
            )

        eligible_indices = self.get_eligible_indices(domain)

        eligible_order = eligible_indices[
            np.argsort(
                rrf_scores[eligible_indices]
            )[::-1]
        ]

        final_order = eligible_order[:top_k]

        return [
            RetrievalResult(
                chunk=self.chunks[int(chunk_index)],
                bm25_rank=bm25_ranks[int(chunk_index)],
                dense_rank=dense_ranks[int(chunk_index)],
                rrf_score=float(rrf_scores[chunk_index])
            )
            for chunk_index in final_order
        ]


def build_retriever() -> HybridRetriever:
    chunks = ingest_knowledge_base()

    return HybridRetriever(chunks)