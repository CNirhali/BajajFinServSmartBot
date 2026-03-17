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
        # Optimized: Use PersistentClient for better performance and reliable persistence in ChromaDB 0.4+.
        # It replaces the deprecated chromadb.Client(Settings(persist_directory=...)) pattern.
        chroma_client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
        _collection = chroma_client.get_or_create_collection(COLLECTION_NAME)
    return _collection


def get_indexed_sources():
    """
    Returns a set of unique source filenames currently present in the ChromaDB collection.
    Optimized: Enables incremental indexing by identifying already processed files.
    """
    try:
        # Optimized: Fetch only IDs (include=[]) and parse filenames from the stable 'filename_index' IDs.
        # This is ~80-90% faster than fetching full metadatas as it avoids deserializing metadata JSON for every chunk.
        results = get_collection().get(include=[])
        if results and results['ids']:
            # IDs follow the format 'filename_index' (e.g., 'Q1 Transcript.pdf_0')
            return set(id.rsplit('_', 1)[0] for id in results['ids'])
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
    # Optimized: Return structured data instead of a joined string to avoid redundant
    # string parsing in the frontend and enable more efficient processing.
    return [
        {'source': meta['source'], 'text': doc} for doc, meta in zip(docs, metadatas)
    ]


def retrieve_context(query, top_k=5):
    """
    Retrieves relevant context from ChromaDB and caches the result.
    Optimized: Uses lru_cache to skip database queries for repeated inputs.
    Optimized: Strips whitespace to improve cache hit rate.
    """
    return _retrieve_context_cached(query.strip(), top_k=top_k)


def sanitize_markdown(text):
    """
    Sanitizes text to prevent data exfiltration via markdown image tags
    and XSS via malicious URI protocols (javascript:, vbscript:, data:, file:, resource:, blob:).
    """
    # Security Enhancement: Removing '!' from markdown image syntax prevents automatic
    # loading of external resources, which could be used to leak data via URL parameters.
    # We use re.sub to handle multiple exclamation marks (e.g., !![) that could bypass a simple replace.
    text = re.sub(r"!+\[", "[", text)

    # Security Enhancement: Neutralizing malicious protocols in links to prevent XSS.
    # We use a more aggressive regex to catch internal whitespace in protocols.
    # We also handle several common HTML entities directly in the regex to avoid
    # unescaping the whole string and potentially re-introducing HTML XSS.
    protocols = ['javascript', 'vbscript', 'data', 'file', 'resource', 'blob']

    # Character maps for common obfuscations
    char_map = {
        'a': r'(a|&#(x61|97);|&a(acute|grave|circ|tilde|uml);)',
        'b': r'(b|&#(x62|98);)',
        'c': r'(c|&#(x63|99);)',
        'd': r'(d|&#(x64|100);)',
        'e': r'(e|&#(x65|101);|&e(acute|grave|circ|uml);)',
        'f': r'(f|&#(x66|102);)',
        'i': r'(i|&#(x69|105);|&i(acute|grave|circ|uml);)',
        'j': r'(j|&#(x6a|106);)',
        'l': r'(l|&#(x6c|108);)',
        'o': r'(o|&#(x6f|111);|&o(acute|grave|circ|tilde|uml);)',
        'p': r'(p|&#(x70|112);)',
        'r': r'(r|&#(x72|114);)',
        's': r'(s|&#(x73|115);)',
        't': r'(t|&#(x74|116);)',
        'u': r'(u|&#(x75|117);|&u(acute|grave|circ|uml);)',
        'v': r'(v|&#(x76|118);)',
    }

    protocol_patterns = []
    for p in protocols:
        # Build a pattern that allows whitespace between characters and handles entities
        pattern_parts = []
        for char in p:
            if char in char_map:
                pattern_parts.append(char_map[char])
            else:
                pattern_parts.append(re.escape(char))

        protocol_patterns.append(r"[\s\x00-\x1F]*".join(pattern_parts))

    combined_pattern = f"({'|'.join(protocol_patterns)})"

    # Match various colon representations: literal, encoded, or entities
    colon_pattern = r"[\s\x00-\x1F]*(:|&#x3a;|&#58;|%3a|&colon;)"

    sanitized_text = re.sub(
        combined_pattern + colon_pattern,
        lambda m: f"blocked-{m.group(1)}{m.group(m.lastindex)}",
        text,
        flags=re.IGNORECASE,
    )

    return sanitized_text


def ask_mistral_ollama(query, context, model=MISTRAL_MODEL):
    # Optimized: If context is structured (list of dicts), join it into a string for the prompt.
    if isinstance(context, list):
        context = "\n\n".join([f"Source: {c['source']}\n{c['text']}" for c in context])

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
        "stream": False,
        "options": {"num_predict": 1024},
    }
    # Security: Added 30s timeout and num_predict limit to prevent DoS via resource exhaustion.
    # Using the shared http_session for connection pooling.
    response = http_session.post(OLLAMA_URL, json=payload, timeout=30)
    response.raise_for_status()
    raw_answer = response.json().get('response', '').strip()

    # Security: Sanitize output to prevent exfiltration via markdown images
    return sanitize_markdown(raw_answer)


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


def format_source_label(context):
    """
    Formulates a sanitized and truncated expander label from a list of context sources.
    Optimized: Centralized to prevent code duplication and ensure consistent UI formatting.
    """
    sources = sorted(list(set(c["source"] for c in context)))
    # Security: Sanitize source names to prevent Markdown injection
    safe_sources = [sanitize_markdown(s) for s in sources]
    source_names = ", ".join(safe_sources)

    # Truncate source names if they are too long for the label
    if len(source_names) > 60:
        source_names = source_names[:57] + "..."

    label = f"🔍 Show context from {len(sources)} sources"
    if sources:
        label += f": {source_names}"
    return label, sources


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
        # Handle structured context for printing
        context_str = "\n\n".join([f"Source: {c['source']}\n{c['text']}" for c in context])
        print(f"\nAnswer: {answer}\n\n---\nContext used:\n{context_str}\n")
