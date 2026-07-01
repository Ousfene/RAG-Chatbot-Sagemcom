"""
Professional Loader: Normalized Data to DuckDB (with Unique IDs)
-------------------------------------------------------------
- Loads all normalized text and table data into DuckDB for RAG/search/analytics.
- Each row has a robust, unique id (SHA256 hash of identifying fields).
- Tables use id TEXT PRIMARY KEY for durability and deduplication.
- Drops and recreates tables for schema safety.
- Logs a summary of records loaded.
"""
import duckdb
import json
from pathlib import Path
import logging
import hashlib

DB_PATH = './data_prep/db/data.duckdb'
TEXTS_DIR = Path('./data_prep/processed/normalized/texts')
TABLES_DIR = Path('./data_prep/processed/normalized/tables')

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("load_to_duckdb")

def make_id(*args):
    """Generate a SHA256 hash from a tuple of identifying fields."""
    return hashlib.sha256("::".join(str(a) for a in args).encode("utf-8")).hexdigest()

def main():
    con = duckdb.connect(DB_PATH)
    # Drop tables if they exist (for schema safety)
    con.execute("DROP TABLE IF EXISTS texts")
    con.execute("DROP TABLE IF EXISTS tables")
    # Create tables with id as TEXT PRIMARY KEY
    con.execute("""
    CREATE TABLE texts (
        id TEXT PRIMARY KEY,
        file_name TEXT,
        file_path TEXT,
        file_type TEXT,
        page INTEGER,
        section INTEGER,
        slide INTEGER,
        sheet INTEGER,
        section_title TEXT,
        sheet_title TEXT,
        content TEXT,
        source_link TEXT
    )
    """)
    con.execute("""
    CREATE TABLE tables (
        id TEXT PRIMARY KEY,
        file_name TEXT,
        file_path TEXT,
        file_type TEXT,
        page INTEGER,
        table_index INTEGER,
        headers JSON,
        rows JSON,
        preview TEXT,
        source_link TEXT
    )
    """)
    # Load texts
    text_count = 0
    for file in TEXTS_DIR.glob('*.json'):
        with open(file, 'r', encoding='utf-8') as f:
            records = json.load(f)
            for rec in records:
                rec_id = make_id(
                    rec.get('file_name'),
                    rec.get('file_path'),
                    rec.get('page'),
                    rec.get('section'),
                    rec.get('slide'),
                    rec.get('sheet'),
                    (rec.get('content') or '')[:100]  # first 100 chars for uniqueness
                )
                try:
                    con.execute("""
                        INSERT INTO texts (id, file_name, file_path, file_type, page, section, slide, sheet, section_title, sheet_title, content, source_link)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        rec_id,
                        rec.get('file_name'),
                        rec.get('file_path'),
                        rec.get('file_type'),
                        rec.get('page'),
                        rec.get('section'),
                        rec.get('slide'),
                        rec.get('sheet'),
                        rec.get('section_title'),
                        rec.get('sheet_title'),
                        rec.get('content'),
                        rec.get('source_link')
                    ))
                    text_count += 1
                except duckdb.ConstraintException:
                    # Duplicate id, skip
                    continue
    logger.info(f"Loaded {text_count} text chunks into DuckDB.")
    # Load tables
    table_count = 0
    for file in TABLES_DIR.glob('*.json'):
        with open(file, 'r', encoding='utf-8') as f:
            rec = json.load(f)
            rec_id = make_id(
                rec.get('file_name'),
                rec.get('file_path'),
                rec.get('page'),
                rec.get('table_index'),
                json.dumps(rec.get('headers')),
                json.dumps(rec.get('rows'))
            )
            try:
                con.execute("""
                    INSERT INTO tables (id, file_name, file_path, file_type, page, table_index, headers, rows, preview, source_link)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    rec_id,
                    rec.get('file_name'),
                    rec.get('file_path'),
                    rec.get('file_type'),
                    rec.get('page'),
                    rec.get('table_index'),
                    json.dumps(rec.get('headers')),
                    json.dumps(rec.get('rows')),
                    rec.get('preview'),
                    rec.get('source_link')
                ))
                table_count += 1
            except duckdb.ConstraintException:
                # Duplicate id, skip
                continue
    logger.info(f"Loaded {table_count} tables into DuckDB.")
    con.close()
    logger.info("✅ All normalized data loaded into DuckDB.")

if __name__ == "__main__":
    main()
