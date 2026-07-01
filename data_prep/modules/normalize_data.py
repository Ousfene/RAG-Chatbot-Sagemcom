"""
Professional Data Normalization Module for RAG Pipelines
-------------------------------------------------------
- Cleans and normalizes text, whitespace, and date formats across all processed data types.
- Ensures source metadata and adds a source_link field for direct linking.
- Logs a summary at the end.
"""
import json
import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from collections import Counter, defaultdict

RAW_DIRS = [
    Path("./data_prep/processed/texts"),
    Path("./data_prep/processed/tables"),
    Path("./data_prep/processed/images"),
    Path("./data_prep/processed/metadata"),
]

NORMALIZED_DIR = Path("./data_prep/processed/normalized")
NORMALIZED_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("normalize_data")

# --- Header/Footer Removal ---
def detect_repetitive_lines(pages: List[str], threshold: float = 0.8, position: str = "both") -> set:
    """
    Detect lines that appear at the top/bottom of >= threshold% of pages.
    position: 'top', 'bottom', or 'both'
    """
    line_counts = Counter()
    total_pages = len(pages)
    for page in pages:
        lines = page.splitlines()
        if position in ("top", "both") and lines:
            line_counts[lines[0].strip()] += 1
        if position in ("bottom", "both") and len(lines) > 1:
            line_counts[lines[-1].strip()] += 1
    repetitive = set()
    for line, count in line_counts.items():
        if line and count / total_pages >= threshold:
            repetitive.add(line)
    return repetitive

def matches_header_footer_pattern(line: str) -> bool:
    patterns = [
        r"^Page \d+ sur \d+$",  # Page X sur Y
        r"Sagemcom Internal Information",  # Company footer
        r"^\d{8,}-S$",  # Document code like 24038006-S
        r"^2- Sagemcom Internal Information.*$",  # Variant
        r"^VERY IMPORTANT:.*$",
        r"^The validity of the present document.*$",
        r"^[-–•]? ?This document and the informations contained are the property of Sagemcom.*$",
        r"^GUIDE SS&T POUR LES RCA( Guide: SST_Qual_0181-B)?$"
    ]
    for pat in patterns:
        if re.search(pat, line):
            return True
    return False

def remove_repetitive_lines(text: str, repetitive_lines: set) -> str:
    lines = text.splitlines()
    removed = []
    # Remove from top
    while lines and (lines[0].strip() in repetitive_lines or matches_header_footer_pattern(lines[0].strip())):
        removed.append(lines[0].strip())
        lines.pop(0)
    # Remove from bottom
    while lines and (lines[-1].strip() in repetitive_lines or matches_header_footer_pattern(lines[-1].strip())):
        removed.append(lines[-1].strip())
        lines.pop()
    if removed:
        logger.info(f"[normalize] Removed header/footer lines: {removed}")
    return "\n".join(lines)

def clean_text(text: str) -> str:
    text = text.replace("\ufeff", "").replace("\u200b", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()

def normalize_date(value: str) -> str:
    patterns = [
        (r"(\d{2})[./-](\d{2})[./-](\d{2,4})", "%d-%m-%Y"),
        (r"([A-Za-z]+)[ -](\d{4})", "%b-%Y")
    ]
    for pattern, fmt in patterns:
        match = re.match(pattern, value)
        if match:
            try:
                return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
            except Exception:
                continue
    return value

def build_source_link(record: Dict[str, Any]) -> str:
    file_path = record.get("file_path")
    if not file_path:
        return ""
    abs_path = Path(file_path).resolve()
    if "page" in record:
        return f"file:///{abs_path.as_posix()}#page={record['page']}"
    if "section" in record:
        return f"file:///{abs_path.as_posix()}#section={record['section']}"
    if "slide" in record:
        return f"file:///{abs_path.as_posix()}#slide={record['slide']}"
    if "sheet" in record:
        return f"file:///{abs_path.as_posix()}#sheet={record['sheet']}"
    return f"file:///{abs_path.as_posix()}"

def ensure_metadata(record: Dict[str, Any], file_type: str) -> Dict[str, Any]:
    if "file_name" not in record and "file_path" in record:
        record["file_name"] = Path(record["file_path"]).name
    if "file_path" not in record and "file_name" in record:
        record["file_path"] = str(Path(record["file_name"]).resolve())
    record["source_link"] = build_source_link(record)
    if file_type in [".png", ".jpg", ".jpeg", ".bmp", ".gif"]:
        record.setdefault("summary", None)
    return record

def normalize_record(record: Dict[str, Any], file_type: str) -> Dict[str, Any]:
    normalized = {}
    for k, v in record.items():
        key = k.strip()
        if isinstance(v, str):
            v = clean_text(v)
            if "date" in key.lower():
                v = normalize_date(v)
        normalized[key] = v
    normalized = ensure_metadata(normalized, file_type)
    return normalized

def normalize_all():
    summary = {"files": 0, "records": 0, "errors": 0}
    for subdir in RAW_DIRS:
        if not subdir.exists():
            continue
        output_subdir = NORMALIZED_DIR / subdir.name
        output_subdir.mkdir(parents=True, exist_ok=True)

        # --- NEW: Detect repetitive lines per file ---
        repetitive_lines = set()

        for file_path in subdir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                logger.warning(f"[!] Skipping bad file {file_path}: {e}")
                summary["errors"] += 1
                continue

            if subdir.name == "texts" and isinstance(data, list):
                pages = []
                for block in data:
                    if isinstance(block, dict) and isinstance(block.get("content"), list):
                        page_text = "\n".join(line.strip() for line in block["content"] if line.strip())
                        pages.append(page_text)
                if pages:
                    repetitive_lines = detect_repetitive_lines(pages, threshold=0.8, position="both")
                    if repetitive_lines:
                        logger.info(f"[normalize] Removing repetitive lines: {repetitive_lines}")

        # --- Process files ---
        for file_path in subdir.glob("*.json"):
            with open(file_path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except Exception as e:
                    logger.warning(f"[!] Skipping bad file {file_path}: {e}")
                    summary["errors"] += 1
                    continue

            if isinstance(data, dict):
                file_type = data.get("file_type", "")
                if "rows" in data and isinstance(data["rows"], list):
                    data["rows"] = [normalize_record(row, file_type) for row in data["rows"]]
                    summary["records"] += len(data["rows"])
                if "content" in data:
                    if isinstance(data["content"], list):
                        data["content"] = [
                            clean_text(line)
                            for line in data["content"]
                            if line.strip() and line.strip() not in repetitive_lines and not matches_header_footer_pattern(line)
                        ]
                    else:
                        data["content"] = clean_text(data["content"])
                data = ensure_metadata(data, file_type)
                summary["records"] += 1

            elif isinstance(data, list):
                file_type = ""
                def is_header_footer_heading(heading, repetitive_lines):
                    if not heading:
                        return False
                    if heading.strip() in repetitive_lines:
                        return True
                    if matches_header_footer_pattern(heading):
                        return True
                    return False
                filtered = []
                for item in data:
                    if not isinstance(item, dict):
                        continue
                    heading = item.get("heading", "")
                    content = item.get("content", [])
                    if isinstance(content, list):
                        content = [
                            clean_text(line)
                            for line in content
                            if line.strip() and not matches_header_footer_pattern(line) and line.strip() not in repetitive_lines
                        ]
                    else:
                        content = clean_text(content)
                    all_content_is_header = all(
                        line.strip() in repetitive_lines or matches_header_footer_pattern(line)
                        for line in content
                    ) if content else True
                    if is_header_footer_heading(heading, repetitive_lines) and all_content_is_header:
                        continue
                    if is_header_footer_heading(heading, repetitive_lines):
                        heading = ""
                    if content:
                        item["heading"] = heading
                        item["content"] = content
                        filtered.append(normalize_record(item, file_type))
                data = filtered
                summary["records"] += len(data)

            else:
                logger.info(f"[skip] Unsupported format in {file_path.name}")
                continue

            out_path = output_subdir / file_path.name
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            summary["files"] += 1
            logger.info(f"[normalized] {file_path.name} → {out_path}")

    logger.info(f"[summary] Files normalized: {summary['files']}, Records: {summary['records']}, Errors: {summary['errors']}")

if __name__ == "__main__":
    normalize_all()
