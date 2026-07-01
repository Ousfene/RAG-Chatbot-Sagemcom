"""
Semantic-Aware Chunking and Quality Filtering for RAG
-----------------------------------------------------
- Splits normalized text into meaningful chunks (paragraphs, sentences, etc.)
- Applies quality checks: length, noise, duplicates, language
- Designed for use after loading from DuckDB, before embedding
"""
import re
import json
from typing import List, Dict, Any
from pathlib import Path

# Optional: import spaCy for sentence/paragraph splitting
try:
    import spacy
    nlp = spacy.blank("fr")  # Use French, or "en" for English, or load a full model for better results
except ImportError:
    nlp = None

# --- Chunking Functions ---
def split_by_paragraph(text: str) -> List[str]:
    """Split text into paragraphs (by double newline or similar)."""
    paras = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    return paras

def split_by_sentence(text: str) -> List[str]:
    """Split text into sentences using spaCy if available, else fallback to regex."""
    if nlp:
        doc = nlp(text)
        return [sent.text.strip() for sent in doc.sents if sent.text.strip()]
    # Fallback: naive split
    return re.split(r'(?<=[.!?])\s+', text)

# --- Quality Filtering Functions ---
def is_good_chunk(chunk: str, min_len: int = 10) -> bool:
    """Filter out empty, too short, or noisy chunks. Do NOT filter out long chunks (split them instead)."""
    chunk = chunk.strip()
    if not chunk:
        return False
    if len(chunk) < min_len:
        return False
    # Filter out mostly non-alphanumeric (noise)
    if len(re.sub(r'[^\w\d]', '', chunk)) / max(1, len(chunk)) < 0.3:
        return False
    return True

# --- Split long chunk helper ---
def split_long_chunk(chunk: str, max_len: int = 1000, overlap: int = 100) -> list:
    """Split a long chunk into smaller pieces with overlap."""
    if len(chunk) <= max_len:
        return [chunk]
    result = []
    start = 0
    while start < len(chunk):
        end = min(start + max_len, len(chunk))
        piece = chunk[start:end]
        result.append(piece)
        if end >= len(chunk):
            break
        start = end - overlap
    return result

def deduplicate_chunks(chunks: List[str]) -> List[str]:
    """Remove near-duplicate chunks (exact match for now)."""
    seen = set()
    result = []
    for c in chunks:
        if c not in seen:
            seen.add(c)
            result.append(c)
    return result

# --- Main Chunking Pipeline ---
def chunk_and_filter(text: str, mode: str = "paragraph", max_len: int = 1000, overlap: int = 100) -> List[str]:
    """
    Split text into chunks and apply quality filters.
    Deduplicate only at the paragraph level.
    Long chunks are split further with overlap.
    mode: 'paragraph' or 'sentence'
    """
    if mode == "sentence":
        chunks = split_by_sentence(text)
        # Do NOT deduplicate at sentence level
        filtered = []
        for c in chunks:
            if is_good_chunk(c):
                filtered.extend(split_long_chunk(c, max_len=max_len, overlap=overlap))
        return filtered
    else:
        chunks = split_by_paragraph(text)
        filtered = []
        for c in chunks:
            if is_good_chunk(c):
                filtered.extend(split_long_chunk(c, max_len=max_len, overlap=overlap))
        filtered = deduplicate_chunks(filtered)  # Deduplicate only at paragraph level
        return filtered

def chunk_json_blocks(json_path: str, min_len: int = 10, max_len: int = 1000, overlap: int = 100) -> list:
    """
    Load a normalized JSON file and chunk its blocks for embedding.
    Returns a list of dicts: {chunk, heading, page, source_link, ...}
    """
    chunks = []
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # If file is a list of blocks
    if isinstance(data, list):
        for block in data:
            content = block.get("content", [])
            if isinstance(content, list):
                text = "\n".join([c.strip() for c in content if c.strip()])
            else:
                text = str(content).strip()
            # Filter out empty blocks
            if not text:
                continue
            # Split long blocks into overlapping chunks
            for chunk in split_long_chunk(text, max_len=max_len, overlap=overlap):
                if is_good_chunk(chunk, min_len=min_len):
                    chunks.append({
                        "chunk": chunk,
                        "heading": block.get("heading", ""),
                        "page": block.get("page", None),
                        "source_link": block.get("source_link", ""),
                        "file_name": block.get("file_name", ""),
                        "file_path": block.get("file_path", ""),
                        "parent_heading": block.get("parent_heading", "")
                    })
    # If file is a dict (e.g., table or metadata)
    elif isinstance(data, dict):
        # For tables: chunk by row
        rows = data.get("rows", [])
        for row in rows:
            row_text = " ".join([str(v).strip() for v in row.values() if v and str(v).strip()])
            if not row_text:
                continue
            for chunk in split_long_chunk(row_text, max_len=max_len, overlap=overlap):
                if is_good_chunk(chunk, min_len=min_len):
                    chunks.append({
                        "chunk": chunk,
                        "table_index": data.get("table_index", None),
                        "page": data.get("page", None),
                        "source_link": data.get("source_link", ""),
                        "file_name": data.get("file_name", ""),
                        "file_path": data.get("file_path", "")
                    })
    return chunks

# Example usage:
# chunks = chunk_json_blocks("data_prep/processed/normalized/texts/SST_Qual_0181_Guide_SST_RCA.json")
# for c in chunks:
#     print(c)
