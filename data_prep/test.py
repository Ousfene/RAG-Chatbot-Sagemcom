from modules.extract_texts import extract_all_texts
from pathlib import Path

print("📄 Running extract_all_texts...")
extract_all_texts(Path("raw_files"), Path("processed/texts"))
print("✅ Done!")
