import requests
import os
import functools
import re

CHROMA_DB_DIR = './chroma_db'
COLLECTION_NAME = 'bfs_smartbot'
EMBED_MODEL = 'all-MiniLM-L6-v2'
OLLAMA_URL = 'http://localhost:11434/api/generate'  # Default Ollama endpoint
MISTRAL_MODEL = 'mistral'  # Change if your model name is different

# Lazy loading for embedding model and ChromaDB to speed up initial import
_embedder = None
_collection = None


def get_embedder():
    """Returns the pre-loaded embedding model, initializing it on first call."""
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        _embedder = SentenceTransformer(EMBED_MODEL)
    return _embedder


def get_collection():
    """Returns the ChromaDB collection, initializing the client on first call."""
    global _collection
    if _collection is None:
        import chromadb
        from chromadb.config import Settings
        chroma_client = chromadb.Client(Settings(persist_directory=CHROMA_DB_DIR))
        _collection = chroma_client.get_or_create_collection(COLLECTION_NAME)
    return _collection


def get_indexed_sources():
    """
    Returns a set of unique source filenames currently present in the ChromaDB collection.
    Optimized: Enables incremental indexing by identifying already processed files.
    """
    try:
        # Fetch metadatas to extract source filenames.
        # Include=['metadatas'] avoids fetching large document texts or embeddings.
        results = get_collection().get(include=['metadatas'])
        if results and results['metadatas']:
            return set(meta['source'] for meta in results['metadatas'])
    except Exception:
        pass
    return set()


# Use a global Session to enable connection pooling for Ollama API calls.
# This reduces latency by reusing established TCP connections for consecutive requests.
http_session = requests.Session()


@functools.lru_cache(maxsize=128)
def _get_query_embedding_cached(query):
    return get_embedder().encode([query])


def get_query_embedding(query):
    """
    Computes and caches the embedding for a given query string.
    Optimized: Uses lru_cache to speed up repeated or similar queries.
    Optimized: Strips whitespace to improve cache hit rate.
    """
    return _get_query_embedding_cached(query.strip())


@functools.lru_cache(maxsize=128)
def _retrieve_context_cached(query, top_k=5):
    # Optimized: Use cached embedding and pass it directly to ChromaDB without list re-wrapping.
    query_emb = get_query_embedding(query)
    results = get_collection().query(query_embeddings=query_emb, n_results=top_k)
    # results['documents'] is a list of lists (one per query)
    docs = results['documents'][0]
    metadatas = results['metadatas'][0]
    context = "\n\n".join([
        f"Source: {meta['source']}\n{doc}" for doc, meta in zip(docs, metadatas)
    ])
    return context


def retrieve_context(query, top_k=5):
    """
    Retrieves relevant context from ChromaDB and caches the result.
    Optimized: Uses lru_cache to skip database queries for repeated inputs.
    Optimized: Strips whitespace to improve cache hit rate.
    """
    return _retrieve_context_cached(query.strip(), top_k=top_k)


def _sanitize_output(text):
    """
    Sanitizes LLM output to prevent data exfiltration via markdown image tags
    and XSS via malicious URI protocols (javascript:, vbscript:, data:).
    """
    # Security Enhancement: Removing '!' from markdown image syntax prevents automatic
    # loading of external resources, which could be used to leak data via URL parameters.
    text = re.sub(r'!\[', '[', text)

    # Security Enhancement: Neutralizing malicious protocols in links to prevent XSS.
    # It handles javascript:, vbscript:, and data: protocols, including those with
    # whitespace between the protocol name and the colon.
    text = re.sub(r'(javascript|vbscript|data)\s*:', r'blocked-\1:', text, flags=re.IGNORECASE)

    return text


def ask_mistral_ollama(query, context, model=MISTRAL_MODEL):
    # Security: Sanitize input to prevent prompt injection by escaping Mistral instruction tags.
    # We escape both [INST] and [/INST] using case-insensitive regex to handle variations.
    inst_pattern = re.compile(r'\[/?INST\]', re.IGNORECASE)

    def escape_tag(match):
        tag = match.group(0)
        if tag.startswith('[/'):
            return tag[:2] + " " + tag[2:]
        return tag[:1] + " " + tag[1:]

    safe_query = inst_pattern.sub(escape_tag, query)
    safe_context = inst_pattern.sub(escape_tag, context)

    # Security Enhancement: Use Mistral-style [INST] tags and clear delimiters to help the model
    # distinguish between instructions and data, mitigating prompt injection risks.
    prompt = f"""[INST] You are a smart assistant for Bajaj Finserv. Use the following context to answer the user's question. If the answer is not in the context, say you don't know.

### Context:
{safe_context}

### Question:
{safe_query} [/INST]
Answer:"""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    # Security: Added 30s timeout to prevent DoS via resource exhaustion if Ollama is unresponsive.
    # Using the shared http_session for connection pooling.
    response = http_session.post(OLLAMA_URL, json=payload, timeout=30)
    response.raise_for_status()
    raw_answer = response.json().get('response', '').strip()

    # Security: Sanitize output to prevent exfiltration via markdown images
    return _sanitize_output(raw_answer)


@functools.lru_cache(maxsize=128)
def _answer_query_cached(query, top_k=5):
    context = retrieve_context(query, top_k=top_k)
    answer = ask_mistral_ollama(query, context)
    return answer, context


def answer_query(query, top_k=5):
    """
    Generates an answer for the query using RAG and caches the final response.
    Optimized: Uses lru_cache to skip both retrieval and LLM calls for repeated questions.
    Optimized: Strips whitespace to improve cache hit rate.
    """
    return _answer_query_cached(query.strip(), top_k=top_k)


def clear_caches():
    """
    Clears all LRU caches for embeddings, retrieval, and answers.
    Should be called whenever the underlying knowledge base is updated.
    """
    _get_query_embedding_cached.cache_clear()
    _retrieve_context_cached.cache_clear()
    _answer_query_cached.cache_clear()


if __name__ == '__main__':
    while True:
        user_query = input("Ask a question about the files (or 'exit'): ")
        if user_query.lower() == 'exit':
            break
        answer, context = answer_query(user_query)
        print(f"\nAnswer: {answer}\n\n---\nContext used:\n{context}\n")
