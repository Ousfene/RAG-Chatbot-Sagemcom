import duckdb
import hashlib
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct
from datetime import datetime
import logging
import os
import json
from chunking import chunk_json_blocks

# === CONFIG ===
DUCKDB_PATH = 'data_prep/db/data.duckdb'
QDRANT_HOST = 'localhost'
QDRANT_PORT = 6333
COLLECTION_NAME = 'my_pro_rag_bot'
EMBED_MODEL_PATH = './local_models/paraphrase-multilingual-MiniLM-L12-v2'
MAX_LEN = 1000
OVERLAP = 200
BATCH_SIZE = 500
CHUNKED_DIR = 'data_prep/processed/normalized'
CHUNKED_SUBDIRS = ['texts', 'tables', 'metadata']

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("build_index")

def make_id(*args):
    return hashlib.sha256("::".join(str(a) for a in args).encode("utf-8")).hexdigest()


def embed_chunks(split_chunks):
    embed_model = HuggingFaceEmbedding(model_name=EMBED_MODEL_PATH)
    texts = [c["text"] for c in split_chunks]
    logger.info(f"Starting embeddings for {len(texts)} chunks...")
    embeddings = embed_model.get_text_embedding_batch(texts)
    logger.info("Embeddings done!")
    return embeddings

def store_in_qdrant(split_chunks, embeddings):
    qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    if qdrant_client.collection_exists(COLLECTION_NAME):
        logger.info("Collection exists. Deleting it...")
        qdrant_client.delete_collection(COLLECTION_NAME)
    qdrant_client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config={"size": len(embeddings[0]), "distance": "Cosine"}
    )
    points = []
    for idx, (chunk, embedding) in enumerate(zip(split_chunks, embeddings)):
        points.append(
            PointStruct(
                id=idx,  # Use integer index as ID for Qdrant
                vector=embedding,
                payload={
                    "text": chunk["text"],
                    **chunk["metadata"]  # SHA256 hash is still in metadata as 'id'
                }
            )
        )
    total = len(points)
    logger.info(f"Uploading {total} vectors in batches of {BATCH_SIZE}...")
    for i in range(0, total, BATCH_SIZE):
        batch = points[i:i + BATCH_SIZE]
        qdrant_client.upsert(collection_name=COLLECTION_NAME, points=batch)
        logger.info(f"Uploaded batch {i}–{i + len(batch) - 1}")
    count = qdrant_client.count(collection_name=COLLECTION_NAME)
    logger.info(f"✅ All done! Final vector count: {count.count}")

# --- New chunk loading function ---
def load_all_chunks(chunked_dir=CHUNKED_DIR, subdirs=CHUNKED_SUBDIRS):
    all_chunks = []
    for subdir in subdirs:
        folder = os.path.join(chunked_dir, subdir)
        if not os.path.exists(folder):
            continue
        for fname in os.listdir(folder):
            if not fname.endswith('.json'):
                continue
            fpath = os.path.join(folder, fname)
            chunks = chunk_json_blocks(fpath)
            all_chunks.extend(chunks)
    return all_chunks

def main():
    logger.info("Starting RAG index build from chunked JSON files...")
    chunks = load_all_chunks()
    logger.info(f"Loaded {len(chunks)} chunks from chunked JSON files.")
    # Prepare for embedding
    split_chunks = []
    for chunk in chunks:
        text = chunk["chunk"]
        if len(text) <= MAX_LEN:
            split_chunks.append({"text": text, "metadata": {k: v for k, v in chunk.items() if k != "chunk"}})
        else:
            start = 0
            while start < len(text):
                end = min(start + MAX_LEN, len(text))
                piece = text[start:end]
                split_chunks.append({"text": piece, "metadata": {k: v for k, v in chunk.items() if k != "chunk"}})
                if end >= len(text):
                    break
                start = end - OVERLAP
    logger.info(f"After splitting: {len(split_chunks)} total chunks.")
    embeddings = embed_chunks(split_chunks)
    store_in_qdrant(split_chunks, embeddings)
    logger.info("RAG index build complete.")

if __name__ == "__main__":
    main()
