import hashlib
import json
from pathlib import Path
from typing import Dict, List, Tuple

from rag.schemas import DocumentChunk

BASE_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_BASE_DIR = BASE_DIR / "knowledge_base"
CATALOG_FILE = KNOWLEDGE_BASE_DIR / "catalog.json"

MAX_CHUNK_CHARS = 900
CHUNK_OVERLAP_CHARS = 120


def load_document_catalog() -> Dict[str, Dict[str, str]]:
    if not CATALOG_FILE.exists():
        return {}

    with CATALOG_FILE.open(encoding="utf-8") as file:
        return json.load(file)


def split_text(text: str) -> List[str]:
    text = text.strip()

    if len(text) <= MAX_CHUNK_CHARS:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + MAX_CHUNK_CHARS, len(text))
        chunks.append(text[start:end].strip())

        if end == len(text):
            break

        start = end - CHUNK_OVERLAP_CHARS

    return chunks


def parse_markdown_sections(
    markdown: str
) -> Tuple[str, List[Dict[str, str]]]:
    title = "Untitled"
    current_section = "Introduction"
    current_lines = []
    sections = []

    for raw_line in markdown.splitlines():
        line = raw_line.strip()

        if line.startswith("# "):
            title = line[2:].strip()

        elif line.startswith("## "):
            content = "\n".join(current_lines).strip()

            if content:
                sections.append({
                    "section": current_section,
                    "content": content
                })

            current_section = line[3:].strip()
            current_lines = []

        else:
            current_lines.append(raw_line)

    content = "\n".join(current_lines).strip()

    if content:
        sections.append({
            "section": current_section,
            "content": content
        })

    return title, sections


def make_chunk_id(
    source: str,
    section: str,
    index: int,
    content: str
) -> str:
    raw_text = f"{source}|{section}|{index}|{content}"

    return hashlib.sha256(
        raw_text.encode("utf-8")
    ).hexdigest()[:16]


def ingest_knowledge_base() -> List[DocumentChunk]:
    all_chunks = []
    catalog = load_document_catalog()

    for file_path in KNOWLEDGE_BASE_DIR.rglob("*.md"):
        markdown = file_path.read_text(encoding="utf-8")
        title, sections = parse_markdown_sections(markdown)

        source = str(file_path.relative_to(BASE_DIR))

        catalog_key = "/".join(
            part.strip()
            for part in file_path.relative_to(
                KNOWLEDGE_BASE_DIR
            ).parts
        )

        document_type = file_path.parent.name.strip()
        document_metadata = catalog.get(catalog_key, {})

        for section_data in sections:
            pieces = split_text(section_data["content"])

            for index, piece in enumerate(pieces):
                chunk = DocumentChunk(
                    chunk_id=make_chunk_id(
                        source,
                        section_data["section"],
                        index,
                        piece
                    ),
                    source=source,
                    document_type=document_type,
                    title=title,
                    section=section_data["section"],
                    content=piece,
                    metadata={
                        "source": source,
                        "document_type": document_type,
                        "domain": document_metadata.get(
                            "domain",
                            "global"
                        ),
                        "authority": document_metadata.get(
                            "authority",
                            document_type
                        ),
                        "owner": document_metadata.get(
                            "owner",
                            "unknown"
                        ),
                        "chunk_index": str(index)
                    }
                )

                all_chunks.append(chunk)

    return all_chunks