"""
Professional Data Preparation Pipeline for RAG
---------------------------------------------
- Orchestrates extraction and normalization steps with logging and CLI.
- Flexible: run all steps or selected steps, specify input/output directories.
- Image extraction is optional (skip for now).
"""
import logging
import argparse
from pathlib import Path

import traceback

# === Import all extractors and normalizer ===
from modules.extract_texts import extract_all_texts
from modules.extract_tables import extract_all_tables
from modules.extract_metadata import extract_metadata_from_all
from modules.normalize_data import normalize_all

# === Future: LLaVA summarizer ===
def summarize_with_llava_stub():
    logger.info("[llava] Skipped (run on other machine)")

RAW_DIR = Path("./data_prep/raw_files")
TEXT_DIR = Path("./data_prep/processed/texts")
TABLE_DIR = Path("./data_prep/processed/tables")
IMAGE_DIR = Path("./data_prep/processed/images")
METADATA_DIR = Path("./data_prep/processed/metadata")
NORMALIZED_DIR = Path("./data_prep/processed/normalized")

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("pipeline")

# === Pipeline Steps ===
def step_extract_texts(raw_dir=RAW_DIR, output_dir=TEXT_DIR):
    logger.info("Step 1: Extracting texts...")
    extract_all_texts(raw_dir, output_dir)
    logger.info("Texts extracted.")

def step_extract_tables(raw_dir=RAW_DIR, output_dir=TABLE_DIR):
    logger.info("Step 2: Extracting tables...")
    extract_all_tables(raw_dir, output_dir)
    logger.info("Tables extracted.")

def step_extract_metadata(raw_dir=RAW_DIR, output_dir=METADATA_DIR):
    logger.info("Step 3: Extracting metadata...")
    extract_metadata_from_all(raw_dir, output_dir)
    logger.info("Metadata extracted.")

def step_normalize_all():
    logger.info("Step 4: Normalizing all outputs...")
    normalize_all()
    logger.info("Normalization complete.")

def step_summarize_llava():
    logger.info("Step 5: Summarize with LLaVA (stub)...")
    summarize_with_llava_stub()
    logger.info("LLaVA placeholder complete.")

# === Main Pipeline ===
def run_pipeline(steps=None):
    logger.info("\n📁 Starting full data preprocessing pipeline...\n")
    summary = {"success": 0, "fail": 0}
    all_steps = [
        ("extract_texts", step_extract_texts),
        ("extract_tables", step_extract_tables),
        ("extract_metadata", step_extract_metadata),
        ("normalize_all", step_normalize_all),
        ("summarize_llava", step_summarize_llava),
    ]
    for name, func in all_steps:
        if steps and name not in steps:
            continue
        try:
            func()
            summary["success"] += 1
        except Exception as e:
            logger.error(f"❌ Step '{name}' failed: {e}")
            traceback.print_exc()
            summary["fail"] += 1
    logger.info(f"\n🎯 Pipeline completed. Success: {summary['success']}, Failures: {summary['fail']}")
    logger.info(f"All outputs are in: {Path('./data_prep/processed').resolve()}")

def main():
    parser = argparse.ArgumentParser(description="Run the full data preparation pipeline for RAG.")
    parser.add_argument(
        "--steps",
        nargs="*",
        default=None,
        help="Pipeline steps to run (extract_texts, extract_tables, extract_metadata, normalize_all, summarize_llava). Default: all."
    )
    args = parser.parse_args()
    run_pipeline(steps=args.steps)

if __name__ == "__main__":
    main()