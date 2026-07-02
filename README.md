# RAG Chatbot — Sagemcom Quality Department

An internal document-aware chatbot built during an internship at 
Sagemcom Software & Technologies Tunisia. Designed to help quality 
engineers query internal documentation with verified, cited answers.

## Features

- **RAG Pipeline** — retrieves relevant chunks from internal PDF 
documents before generating answers
- **Citation System** — every answer includes exact PDF filename 
and page number for verification
- **Multilingual** — automatically detects Arabic, French, or 
English queries without manual configuration
- **Vision Language Model** — handles image and table extraction 
from PDF documents
- **Authentication** — login system restricting access to 
authorized users

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI |
| Frontend | React, Vite |
| Embedding Model | BGE-M3 (local) |
| LLM | Qwen + Vision Language Model |
| Vector Store | LlamaIndex |
| Database | DuckDB |

## Project Structure

├── UI/
│   ├── backend/          # FastAPI application
│   └── frontend/         # React frontend
├── data_prep/            # PDF processing pipeline
│   └── modules/          # Extract text, tables, images, metadata
├── embedding/            # Chunking and index building
├── chatbot.py            # Core RAG logic
└── backend.py            # Main backend entry point

## Setup

1. Clone the repository
2. Download BGE-M3 model and place in `local_models/bge-m3/`
3. Install dependencies: `pip install -r all_requirments/requirments.txt`
4. Run data pipeline: `python data_prep/pipeline.py`
5. Build embeddings: `python embedding/build_index.py`
6. Start backend: `python backend.py`
7. Start frontend: `cd UI/frontend && npm install && npm run dev`

## Note

Model files are not included in this repository due to size 
constraints. Download BGE-M3 from HuggingFace: 
`BAAI/bge-m3`
