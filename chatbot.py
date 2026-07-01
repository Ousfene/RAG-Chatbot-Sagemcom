import os
from llama_index.core import VectorStoreIndex, PromptTemplate
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.ollama import Ollama
from qdrant_client import QdrantClient
from html import escape
# === CONFIG ===
EMBED_MODEL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "local_models/paraphrase-multilingual-MiniLM-L12-v2"))
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION_NAME = "my_pro_rag_bot"
LLM_MODEL = "gemma:2b"
TOP_K = 5

# === System Prompt ===
prompt_template = PromptTemplate(
    """
You are a factual assistant.
You ONLY use the context below to answer.
NEVER invent info not present.

If a summary is present in the context, use it to answer.
If the question explicitly asks for a table, show the table as Markdown.
If no summary is present and the context contains a table, prefer to show the table as Markdown.

If you see a section starting with "=== START TABLE ===" and ending with "=== END TABLE ===",
read it carefully as a table.
Extract the rows, read each row, and summarize them clearly.

If the context does not contain enough, say: "I don't know based on the context."

Always answer in the same language as the user's question.

Previous chat history:
{history}

Context:
{context}

Question:
{question}

Answer:
"""
)


# === Backend factory ===
def get_chatbot_backend():
    """Builds and returns backend objects (index, LLM, prompt)."""
    embed_model = HuggingFaceEmbedding(model_name=EMBED_MODEL_PATH)
    qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    vector_store = QdrantVectorStore(client=qdrant_client, collection_name=COLLECTION_NAME)

    index = VectorStoreIndex.from_vector_store(vector_store=vector_store, embed_model=embed_model)

    llm_instance = Ollama(
        model=LLM_MODEL,
        additional_kwargs={"num_ctx": 1024},
        temperature=0.1,
        max_tokens=256,
        request_timeout=1000
    )

    return {
        "index": index,
        "llm": llm_instance,
        "prompt_template": prompt_template
    }


# === Core function to answer ===
def get_bot_answer(backend, question, history):
    """Retrieve context + generate an answer. Returns (answer, sources_html)."""
    if question.strip().lower() in ["hi", "hello", "hey"]:
        return "👋 Salut ! Que voulez-vous savoir ?", ""

    index = backend["index"]
    llm = backend["llm"]
    prompt_template = backend["prompt_template"]

    # Hybrid retrieval
    retriever = index.as_retriever(similarity_top_k=TOP_K, use_hybrid=True)
    nodes = retriever.retrieve(question)

    if not nodes:
        return "Je n'ai rien trouvé pour cette question. Essayez de reformuler.", ""

    # Build context + sources
    context_parts, sources = [], []
    for node in nodes:
        meta = node.metadata
        file_name = meta.get('file_name') or meta.get('pdf') or "Unknown.pdf"
        page = meta.get('page', 1)
        try:
            page_num = int(page)
        except Exception:
            page_num = 1

        pdf_path = f"./pdfs/{file_name}" if os.path.exists(f"./pdfs/{file_name}") else None

        if pdf_path:
            # produce safe plain text for source display (no clickable styling)
            text = f"{file_name} p.{page_num}"
            safe_text = escape(text)   # avoid accidental HTML injection
            sources.append(safe_text)

        context_parts.append(
            f"**Source:** {file_name} p.{page_num} | Type: {meta.get('type')}\n{node.text}"
        )

    # Keep max 2 sources
    sources = list(dict.fromkeys(sources))[:2]

    # Format history
    history_str = ""
    for pair in history[-3:]:
        history_str += f"User: {pair[0]}\nAssistant: {pair[1]}\n"

    # Final prompt
    messages = prompt_template.format_messages(
        history=history_str,
        context="\n\n".join(context_parts),
        question=question
    )

    try:
        answer = llm.chat(messages).message.content
    except Exception as e:
        answer = f"[Erreur LLM] {e}"

    sources_html = "<br>".join(sources) if sources else ""

    return answer, sources_html


# === Chat wrapper for Gradio/React ===
def chat_with_bot(message, history):
    """Handles one chat turn."""
    if not message.strip():
        return "", history or [], ""

    history = history or []
    cleaned_history, user_msg = [], None
    for msg in history:
        if msg["role"] == "user":
            user_msg = msg["content"]
        elif msg["role"] == "assistant" and user_msg:
            cleaned_history.append([user_msg, msg["content"]])

    backend = get_chatbot_backend()
    try:
        bot_message, sources_html = get_bot_answer(backend, message, cleaned_history)
        history.append({"role": "assistant", "content": f"✨ {bot_message}"})
    except Exception as e:
        history.append({"role": "assistant", "content": f"❌ Erreur: {e}"})
        sources_html = ""

    return "", history, sources_html
