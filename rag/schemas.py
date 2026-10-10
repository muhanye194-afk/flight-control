from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class DocumentChunk:
    chunk_id: str
    source: str
    document_type: str
    title: str
    section: str
    content: str
    metadata: Dict[str, str]


@dataclass
class RetrievalResult:
    chunk: DocumentChunk
    bm25_rank: Optional[int] = None
    dense_rank: Optional[int] = None
    rrf_score: float = 0.0
    rerank_score: Optional[float] = None