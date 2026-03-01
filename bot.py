import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import requests
import os

CHROMA_DB_DIR = './chroma_db'
COLLECTION_NAME = 'bfs_smartbot'
EMBED_MODEL = 'all-MiniLM-L6-v2'
OLLAMA_URL = 'http://localhost:11434/api/generate'  # Default Ollama endpoint
MISTRAL_MODEL = 'mistral'  # Change if your model name is different

# Load embedding model and ChromaDB
embedder = SentenceTransformer(EMBED_MODEL)
chroma_client = chromadb.Client(Settings(persist_directory=CHROMA_DB_DIR))
collection = chroma_client.get_or_create_collection(COLLECTION_NAME)

# Use a global Session to enable connection pooling for Ollama API calls.
# This reduces latency by reusing established TCP connections for consecutive requests.
http_session = requests.Session()


def retrieve_context(query, top_k=5):
    query_emb = embedder.encode([query]).tolist()[0]
    results = collection.query(query_embeddings=[query_emb], n_results=top_k)
    # results['documents'] is a list of lists (one per query)
    docs = results['documents'][0]
    metadatas = results['metadatas'][0]
    context = "\n\n".join([
        f"Source: {meta['source']}\n{doc}" for doc, meta in zip(docs, metadatas)
    ])
    return context


def ask_mistral_ollama(query, context, model=MISTRAL_MODEL):
    prompt = f"""
You are a smart assistant for Bajaj Finserv. Use the following context to answer the user's question. If the answer is not in the context, say you don't know.

Context:
{context}

Question: {query}
Answer:
"""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    # Security: Added 30s timeout to prevent DoS via resource exhaustion if Ollama is unresponsive
    response = requests.post(OLLAMA_URL, json=payload, timeout=30)
    # Using the shared http_session for connection pooling
    response = http_session.post(OLLAMA_URL, json=payload)
    response.raise_for_status()
    return response.json().get('response', '').strip()


def answer_query(query, top_k=5):
    context = retrieve_context(query, top_k=top_k)
    answer = ask_mistral_ollama(query, context)
    return answer, context

if __name__ == '__main__':
    while True:
        user_query = input("Ask a question about the files (or 'exit'): ")
        if user_query.lower() == 'exit':
            break
        answer, context = answer_query(user_query)
        print(f"\nAnswer: {answer}\n\n---\nContext used:\n{context}\n") 