import os
from llama_index.core import VectorStoreIndex
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from qdrant_client import QdrantClient

from langchain_ollama import ChatOllama
from langchain_huggingface import HuggingFaceEmbeddings

from ragas import evaluate
from ragas.metrics import (
    context_precision,
    context_recall,
    answer_relevancy,
    faithfulness,
    answer_correctness,
)
from datasets import Dataset

# ✅ Local embedding for indexing
index_embed_model = HuggingFaceEmbedding(model_name="./local_models/bge-m3")

# ✅ Local embedding for RAGAS
ragas_embed = HuggingFaceEmbeddings(model_name="./local_models/bge-m3")

# ✅ Local LLM — make sure Ollama is running and `gemma:2b` is pulled
local_llm = ChatOllama(
    model="gemma:2b",
    base_url="http://localhost:11434",
)

# ✅ Local vector DB
qdrant_client = QdrantClient(host="localhost", port=6333)
vector_store = QdrantVectorStore(
    client=qdrant_client,
    collection_name="my_local_chatbot",
)
index = VectorStoreIndex.from_vector_store(
    vector_store=vector_store,
    embed_model=index_embed_model
)

# ✅ Your test questions
tutorial_tests = [
    {
        "question": "What is Python?",
        "ground_truth": "Python is an easy to learn, powerful programming language.",
        "reference": "Python is an easy to learn, powerful programming language."
    },
    {
        "question": "What is a list in Python?",
        "ground_truth": "A list is a built-in mutable sequence type in Python.",
        "reference": "A list is a built-in mutable sequence type in Python."
    },
]

questions, answers, contexts, ground_truths, references = [], [], [], [], []

# ✅ Loop
for test in tutorial_tests:
    q = test["question"]
    gt = test["ground_truth"]
    ref = test["reference"]

    # 🔍 Retrieve context
    nodes = index.as_retriever(similarity_top_k=3).retrieve(q)
    ctxs = [n.text for n in nodes]

    print(f"\n🔍 {q}")
    for idx, chunk in enumerate(ctxs):
        print(f"  Chunk {idx+1}: {chunk[:100]}...")

    # ✅ Get local LLM answer
    answer = local_llm.invoke(q).content.strip()

    questions.append(q)
    answers.append(answer)
    contexts.append(ctxs)
    ground_truths.append([gt])
    references.append(ref)

# ✅ Wrap dataset
dataset = Dataset.from_dict({
    "question": questions,
    "answer": answers,
    "contexts": contexts,
    "ground_truths": ground_truths,
    "reference": references,
})

# ✅ Evaluate locally
results = evaluate(
    dataset=dataset,
    metrics=[
        context_precision,
        context_recall,
        answer_relevancy,
        faithfulness,
        answer_correctness,
    ],
    embeddings=ragas_embed,
    llm=local_llm,
)

print("\n✅✅✅ FINAL LOCAL RAGAS RESULTS ✅✅✅")
print(results)
