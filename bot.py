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

# Pre-compiled regex patterns for performance
# Used in sanitize_markdown to prevent data exfiltration via image tags
RE_MD_IMAGE = re.compile(r"!+\[")
# Used in ask_mistral_ollama to escape Mistral instruction tags
RE_INST_TAG = re.compile(r"\[/?INST\]", re.IGNORECASE)

# Protocols to block in markdown links for security
PROTOCOLS = ['javascript', 'vbscript', 'data', 'file', 'resource', 'blob']


def _build_protocol_regex():
    """
    Builds a robust regex to detect dangerous URI protocols even with obfuscation
    via internal whitespace, control characters, or various HTML entity formats.
    """
    protocol_patterns = []
    for p in PROTOCOLS:
        pattern_parts = []
        for char in p:
            c_low = ord(char.lower())
            c_up = ord(char.upper())
            # Match character literally or as numeric entities (decimal/hex)
            # handles optional padding and case-insensitive hex for both cases.
            # e.g. for 'a': a, A, &#97;, &#097;, &#x61;, &#X0061;, &#65;, &#x41;
            char_variants = [
                re.escape(char.lower()),
                re.escape(char.upper()),
                f"&#0*{c_low};",
                f"&#[xX]0*{c_low:x};",
                f"&#0*{c_up};",
                f"&#[xX]0*{c_up:x};",
            ]
            pattern_parts.append(f"(?:{'|'.join(char_variants)})")
        # Allow whitespace and control characters between protocol characters
        protocol_patterns.append(r"[\s\x00-\x1F]*".join(pattern_parts))

    combined_pattern = f"(?:{'|'.join(protocol_patterns)})"
    # Match various colon representations: literal, encoded, entities with padding/case-insensitivity
    # e.g. :, %3a, &#x3a;, &#058;, &colon;
    colon_variants = [
        ":",
        "%3a",
        "&#0*58;",
        "&#[xX]0*3a;",
        "&colon;",
    ]
    colon_pattern = rf"[\s\x00-\x1F]*(?:{'|'.join(colon_variants)})"
    return re.compile(combined_pattern + colon_pattern, re.IGNORECASE)


# Pre-compiled aggressive protocol sanitization regex
RE_PROTOCOL_SAN = _build_protocol_regex()


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
    # We use RE_MD_IMAGE to handle multiple exclamation marks (e.g., !![) that could bypass a simple replace.
    text = RE_MD_IMAGE.sub("[", text)

    # Security Enhancement: Neutralizing malicious protocols in links to prevent XSS.
    # It handles javascript:, vbscript:, data:, file:, resource:, and blob: protocols.
    # We use a robust, pre-compiled regex (RE_PROTOCOL_SAN) that handles common obfuscation
    # techniques like internal whitespace, control characters, and various HTML entity formats.
    # We prefix the matched protocol and colon with 'blocked-' to neutralize it.
    sanitized_text = RE_PROTOCOL_SAN.sub(lambda m: f"blocked-{m.group(0)}", text)

    return sanitized_text


def ask_mistral_ollama(query, context, model=MISTRAL_MODEL):
    # Optimized: If context is structured (list of dicts), join it into a string for the prompt.
    if isinstance(context, list):
        context = "\n\n".join([f"Source: {c['source']}\n{c['text']}" for c in context])

    # Security: Sanitize input to prevent prompt injection by escaping Mistral instruction tags.
    # We escape both [INST] and [/INST] using case-insensitive regex (RE_INST_TAG) to handle variations.
    def escape_tag(match):
        tag = match.group(0)
        if tag.startswith("[/"):
            return tag[:2] + " " + tag[2:]
        return tag[:1] + " " + tag[1:]

    safe_query = RE_INST_TAG.sub(escape_tag, query)
    safe_context = RE_INST_TAG.sub(escape_tag, context)

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
    # Affordance: Add icons based on file type for better visual scannability.
    safe_sources = []
    for s in sources:
        icon = "📊" if s.lower().endswith(".csv") else "📄"
        safe_sources.append(f"{icon} {sanitize_markdown(s)}")
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
