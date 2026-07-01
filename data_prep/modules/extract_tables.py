"""
Professional Table Extraction Module for RAG Pipelines
-----------------------------------------------------
- Extracts tables from PDFs using Camelot, with OCR fallback for broken cells.
- Outputs one JSON per table, with full metadata and a preview field.
- Logs a summary at the end.
"""
import camelot
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import tempfile
import time
import gc
import hashlib
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
import json
from datetime import datetime

OUTPUT_DIR = Path("./data_prep/processed/tables")
RAW_DIR = Path("raw_files")

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("extract_tables")

ocr_cache: Dict[str, str] = {}

def compute_file_hash(path: Path, block_size: int = 65536) -> str:
    sha = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(block_size), b''):
            sha.update(block)
    return sha.hexdigest()

def get_file_metadata(path: Path) -> dict:
    stat = path.stat()
    return {
        "file_name": path.name,
        "file_path": str(path.resolve()),
        "file_type": path.suffix.lower(),
        "file_size": stat.st_size,
        "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "extraction_time": datetime.now().isoformat(),
        "content_hash": compute_file_hash(path),
    }

def is_broken(text: str) -> bool:
    return not text or not text.strip() or len(text.strip()) <= 2

def fallback_ocr_with_cache(pdf_path: Path, page_number: int, row_idx: int, col_idx: int) -> Optional[str]:
    temp_path = None
    doc = None
    try:
        doc = fitz.open(pdf_path)
        page = doc[page_number - 1]
        mat = fitz.Matrix(2.0, 2.0)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_img:
            temp_path = tmp_img.name
            pix.save(temp_path)
        del pix
        with Image.open(temp_path) as img:
            img.load()
            img.close()  # Explicitly close the image to release the file handle
            img_bytes = img.tobytes()
            img_hash = hashlib.md5(img_bytes).hexdigest()
            if img_hash in ocr_cache:
                return ocr_cache[img_hash]
            ocr_text = pytesseract.image_to_string(img)
            clean_text = ocr_text.strip() if ocr_text else None
            if not clean_text:
                ocr_cache[img_hash] = None
                return None
            ocr_cache[img_hash] = clean_text
            return clean_text
    except Exception as e:
        logger.warning(f"[OCR] Failed on page {page_number}, cell r{row_idx} c{col_idx}: {e}")
        return None
    finally:
        if doc:
            doc.close()
        if temp_path and Path(temp_path).exists():
            for retry in range(10):  # Increase retries to 10
                try:
                    with open(temp_path, 'rb') as _f:
                        pass
                    Path(temp_path).unlink()
                    break
                except PermissionError as e:
                    logger.warning(f"[warn] Retry {retry+1}/10: Failed to delete temp file {temp_path}: {e}")
                    time.sleep(1)  # Increase wait to 1 second
                    gc.collect()
                except Exception as e:
                    logger.warning(f"[warn] Failed to delete temp file {temp_path}: {e}")
                    break

def extract_tables(
    pdf_path: Path,
    output_dir: Path = OUTPUT_DIR,
    pages: str = "all"
) -> List[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata = get_file_metadata(pdf_path)
    output_files = []
    # Try both Camelot flavors: lattice first, then stream for fallback
    tables = camelot.read_pdf(str(pdf_path), pages=pages, flavor='lattice', strip_text='\n')
    if len(tables) < 1:
        logger.info(f"[fallback] Trying stream flavor for {pdf_path.name}")
        tables = camelot.read_pdf(str(pdf_path), pages=pages, flavor='stream', strip_text='\n')
    blocks = []
    for i, table in enumerate(tables):
        df = table.df
        if df.shape[0] < 2:
            logger.warning(f"[skip] Table {i+1} in {pdf_path.name} is too small or malformed. Skipping.")
            continue
        headers = df.iloc[0].tolist()
        rows = df.iloc[1:].to_dict(orient="records")
        # OCR fallback for broken cells
        for row_idx, row in enumerate(rows):
            for col_idx, (key, val) in enumerate(row.items()):
                if is_broken(val):
                    cell_text = fallback_ocr_with_cache(pdf_path, table.page, row_idx + 1, col_idx)
                    logger.info(f"[OCR fallback] Cell p{table.page} r{row_idx+1} c{col_idx} → '{cell_text}'")
                    rows[row_idx][key] = cell_text if cell_text and cell_text.strip() else None
        # Add a preview field (first non-empty cell as snippet)
        preview = None
        for row in rows:
            for val in row.values():
                if val and str(val).strip():
                    preview = str(val).strip()
                    break
            if preview:
                break
        blocks.append({
            **metadata,
            "table_index": i + 1,
            "type": "table",
            "page": table.page,
            "headers": headers,
            "rows": rows,
            "preview": preview
        })
    for idx, block in enumerate(blocks):
        output_path = output_dir / f"{pdf_path.stem}_table_{idx + 1}.json"
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(block, f, indent=2, ensure_ascii=False)
        output_files.append(output_path)
    logger.info(f"Extracted {len(blocks)} tables from {pdf_path.name} with fallback OCR where needed.")
    return output_files

def extract_all_tables(
    raw_dir: Path = RAW_DIR,
    output_dir: Path = OUTPUT_DIR
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_files = list(raw_dir.rglob("*.pdf"))
    logger.info(f"Found {len(pdf_files)} PDF files in {raw_dir}")
    total_tables = 0
    errors = 0
    for pdf_path in pdf_files:
        try:
            output_files = extract_tables(pdf_path, output_dir)
            total_tables += len(output_files)
        except Exception as ex:
            logger.error(f"[FAIL] {pdf_path.name}: {ex}")
            errors += 1
    logger.info(f"[summary] PDFs processed: {len(pdf_files)}, Tables extracted: {total_tables}, Errors: {errors}")

if __name__ == "__main__":
    extract_all_tables()
