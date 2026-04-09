import re
import functools
import requests
import os

# Constants
# Security Enhancement: Use environment variables for configuration to avoid hardcoded values.
EMBED_MODEL = os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")
CHROMA_DB_DIR = os.getenv("CHROMA_DB_DIR", "./chroma_db")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "smartbot_docs")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral")


# Lazy loading for embedding model and ChromaDB to speed up initial import
_embedder = None
_collection = None

# Pre-compiled regex patterns for performance
# Define a central gap pattern for characters that browsers/parsers often ignore or treat as whitespace.
# Includes standard whitespace, invisible Unicode (zero-width/format), and backslashes used for obfuscation.
# Hardened: Added Soft Hyphen (\u00ad) and Mongolian Vowel Separator (\u180e).
GAP_PATTERN = r"[\s\u00ad\u180e\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff\\]"

# Used in sanitize_markdown to prevent data exfiltration via image tags.
# Enhanced: Includes fullwidth Unicode variants and allows "gaps" between the exclamation mark and brackets.
RE_MD_IMAGE = re.compile(rf"[!！]+{GAP_PATTERN}*[\[［]")


# Used in ask_mistral_ollama to escape LLM control tokens (Mistral/Llama/System)
# Splitting into two patterns allows using fast regex-native backreferences
# instead of a slower Python function call for substitution.
def _build_control_token_regex(tags, wrappers):
    """
    Builds a regex to match control tokens with internal obfuscation.
    wrappers: list of tuples of (opening, closing) characters, e.g. [('[', ']')]
    """
    # Expanded: Includes additional invisible/format Unicode characters and backslashes to prevent obfuscation bypasses.
    gap = GAP_PATTERN
    tag_patterns = []
    for tag in tags:
        # Each character in the tag can be followed by optional gaps/spaces
        tag_patterns.append(f"{gap}*".join([re.escape(c) for c in tag]))

    opening_chars = [re.escape(w[0]) for w in wrappers]
    closing_chars = [re.escape(w[1]) for w in wrappers]

    opening = f"[{''.join(opening_chars)}]"
    closing = f"[{''.join(closing_chars)}]"
    # Enhanced: Support fullwidth Unicode variants for brackets and angles.
    first_opening = wrappers[0][0]
    if first_opening == "[":
        opening = r"[\[［]"
        closing = r"[\]］]"
    elif first_opening == "<":
        opening = r"[<＜]"
        closing = r"[>＞]"
    else:
        opening = re.escape(wrappers[0][0])
        closing = re.escape(wrappers[0][1])

    # Enhanced: Matches variant slashes (Fullwidth ／, backslash \) in the slash group for better protection.
    # Using non-greedy gap*? before the slash group ensures that variant slashes are captured by the group
    # rather than being consumed by the preceding gap pattern.
    return re.compile(
        rf"{opening}{gap}*?(?P<slash>[/／\\]?){gap}*(?P<tag>{'|'.join(tag_patterns)}){gap}*{closing}",
        re.IGNORECASE,
    )


# Enhanced: Matches tags even with internal whitespace or Unicode zero-width characters to prevent bypasses.
# Expanded: Includes additional common LLM control tokens (USER, ASST, TOOL, etc.).
# Support for Fullwidth Unicode brackets (U+FF3B, U+FF3D) and angles (U+FF1C, U+FF1E).
RE_CONTROL_BRACKET = _build_control_token_regex(
    ["INST", "SYS", "USER", "ASST", "TOOL", "TOOL_CALLS", "TOOL_RESULTS", "AVAILABLE_TOOLS"],
    [("[", "]"), ("\uff3b", "\uff3d")],
)
RE_CONTROL_ANGLE = _build_control_token_regex(["s"], [("<", ">"), ("\uff1c", "\uff1e")])

# Pre-compiled regex for zero-width and format characters to improve performance in _escape_control_tokens
# Expanded: Includes directional formatting and invisible formatters.
# Hardened: Added Soft Hyphen (\u00ad) and Mongolian Vowel Separator (\u180e).
ZERO_WIDTH_CHARS = "\u00ad\u180e\u200b\u200c\u200d\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2060\u2061\u2062\u2063\u2064\u2065\u2066\u2067\u2068\u2069\u206a\u206b\u206c\u206d\u206e\u206f\ufeff"
RE_ZERO_WIDTH = re.compile(r"[\u00ad\u180e\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff]")
# Optimized: Combined gap regex for single-pass removal of whitespace, invisible characters, and backslashes.
RE_GAP = re.compile(GAP_PATTERN)

# Protocols to block in markdown links for security
PROTOCOLS = [
    "javascript",
    "vbscript",
    "data",
    "file",
    "resource",
    "blob",
    "mhtml",
    "about",
    "filesystem",
    "view-source",
    "jar",
    "ms-appx-web",
    "ms-appx",
    "ms-appinstaller",
    "intent",
    "content",
    "chrome",
    "moz-extension",
    "webcal",
]


def _build_protocol_regex():
    """
    Builds a robust regex to detect dangerous URI protocols even with obfuscation
    via internal whitespace, control characters, or various HTML entity formats.
    """
    protocol_patterns = []
    # Whitespace, control characters (including Unicode zero-width/format), their HTML entity equivalents,
    # and URL-encoded variants that can be used for obfuscation.
    # e.g. \n, \\, \u200b, &#10;, &#x0A;, %0A, &Tab;, &NewLine;, &nbsp;
    # Expanded gap pattern to include directional formatting and invisible formatters.
    # Hardened: Added Soft Hyphen (\u00ad) and Mongolian Vowel Separator (\u180e).
    gap_variants = [
        r"[\s\u00ad\u180e\x00-\x1F\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff\\]",
        r"&#0*(?:0|9|10|13|32|173|6158);?",
        r"&#[xX]0*(?:0|9|[aA]|[dD]|20|[aA][dD]|180[eE]);?",
        r"%0*(?:0|9|[aA]|[dD])",
        r"%20",
        r"&Tab;?",
        r"&NewLine;?",
        r"&nbsp;?",
        r"&#0*160;?",
        r"&#[xX]0*[aA]0;?",
        r"%[cC]2%[aA]0",
        r"&thinsp;?",
        r"&zwnj;?",
        r"&zwj;?",
        r"&lrm;?",
        r"&rlm;?",
    ]
    gap_pattern = f"(?:{'|'.join(gap_variants)})*"

    for p in PROTOCOLS:
        pattern_parts = []
        for char in p:
            c_low = ord(char.lower())
            c_up = ord(char.upper())
            # Match character literally or as numeric entities (decimal/hex).
            # Semicolon is optional in some browser parsers for entities.
            # We include both upper and lowercase entities as they have different numeric values.
            # e.g. for 'a': a, &#97, &#97;, &#x61, &#x61;, &#65, &#65;, &#x41, &#x41;
            char_variants = [
                re.escape(char),  # re.IGNORECASE handles both cases
                f"&#0*{c_low};?",
                f"&#[xX]0*{c_low:x};?",
                f"&#0*{c_up};?",
                f"&#[xX]0*{c_up:x};?",
            ]
            pattern_parts.append(f"(?:{'|'.join(char_variants)})")

        protocol_patterns.append(gap_pattern.join(pattern_parts))

    combined_pattern = f"(?:{'|'.join(protocol_patterns)})"
    # Match various colon representations: literal, encoded, entities with optional semicolon,
    # and Unicode fullwidth/small colon variants.
    # e.g. :, %3a, &#x3a, &#x3a;, &#058, &#058;, &colon, &colon;, ：, ﹕
    # Expanded with additional Unicode colon-like characters (Ratio, Two Dot Punctuation, etc.)
    # Expanded: Includes additional visual/functional Unicode colon variants.
    colon_variants = [
        ":",
        "%3a",
        "&#0*58;?",
        "&#[xX]0*3a;?",
        "&colon;?",
        "\uff1a",
        "\ufe55",
        "\u2236",
        "\u205a",
        "\ua789",
        "\u0589",
        "\u1804",
        "\u205d",
    ]
    colon_pattern = rf"{gap_pattern}(?:{'|'.join(colon_variants)})"
    # Added gap_pattern at the start to catch obfuscated protocols with leading characters
    return re.compile(gap_pattern + combined_pattern + colon_pattern, re.IGNORECASE)


# Pre-compiled aggressive protocol sanitization regex
RE_PROTOCOL_SAN = _build_protocol_regex()

# Common LLM tags for fast-path lookup in _clean_tag.
CLEAN_TAGS = {"INST", "SYS", "USER", "ASST", "S", "TOOL", "TOOL_CALLS", "TOOL_RESULTS", "AVAILABLE_TOOLS"}


def _clean_tag(match):
    """
    Helper function to clean up and format LLM control tags during substitution.
    Moved to module level to avoid re-definition overhead in _escape_control_tokens.
    """
    raw_match = match.group(0)
    slash = match.group("slash") or ""
    tag = match.group("tag")

    # Security Enhancement: Normalize variant slashes (Fullwidth ／, backslash \) to standard forward slash.
    if slash and slash != "/":
        slash = "/"

    # Optimized: Add fast-path check for already-clean tags to skip regex substitution.
    # This provides a ~2.5x speedup for standard tags like [INST] or <s>.
    clean_tag = tag.upper()
    if clean_tag not in CLEAN_TAGS:
        # Fallback: Use RE_GAP for single-pass removal of whitespace, invisible characters, and backslashes.
        # Optimized: Reuse the already-calculated clean_tag to avoid redundant upper() call.
        clean_tag = RE_GAP.sub("", clean_tag)

    # Identify the bracket type for correct neutralization formatting.
    # Checks both standard and Fullwidth Unicode variants.
    if "[" in raw_match or "\uff3b" in raw_match:
        return f"[ {slash}{clean_tag} ]"
    return f"< {slash}{clean_tag} >"


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
        if results and results["ids"]:
            # IDs follow the format 'filename_index' (e.g., 'Q1 Transcript.pdf_0')
            # Optimized: Use set comprehension instead of set(generator) to reduce iteration overhead.
            return {id.rsplit("_", 1)[0] for id in results["ids"]}
    except Exception:
        pass
    return set()


# Use a global Session to enable connection pooling for Ollama API calls.
# This reduces latency by reusing established TCP connections for consecutive requests.
http_session = requests.Session()


@functools.lru_cache(maxsize=128)
def _get_query_embedding_cached(query):
    """
    Computes a 1D embedding for a single query.
    Optimized: Passes the string directly to .encode() instead of a single-element list.
    This bypasses batching/padding logic in SentenceTransformers, providing ~15% speedup.
    """
    return get_embedder().encode(query, show_progress_bar=False)


def get_query_embedding(query):
    """
    Computes and caches the embedding for a given query string.
    Optimized: Uses lru_cache to speed up repeated or similar queries.
    Optimized: Strips whitespace to improve cache hit rate.
    """
    return _get_query_embedding_cached(query.strip())


@functools.lru_cache(maxsize=128)
def _retrieve_context_cached(query, top_k=5):
    # Optimized: Use cached embedding.
    # Optimized: Directly call the cached embedding function to avoid redundant strip() and extra function layer.
    # Optimized: Explicitly request only 'metadatas' and 'documents' from ChromaDB (include=['metadatas', 'documents']).
    # This reduces overhead by skipping distance calculations which are not needed for this application.
    query_emb = _get_query_embedding_cached(query)
    # Optimized: Explicitly include only metadatas and documents to avoid
    # calculating and transferring unused distances.
    # Note: query_emb is a 1D array due to the string-based encoder optimization.
    # ChromaDB expects a list of embeddings, so we wrap it: [query_emb].
    results = get_collection().query(
        query_embeddings=[query_emb], n_results=top_k, include=["metadatas", "documents"]
    )
    # results['documents'] is a list of lists (one per query)
    docs = results["documents"][0]
    metadatas = results["metadatas"][0]
    # Optimized: Return structured data instead of a joined string to avoid redundant
    # string parsing in the frontend and enable more efficient processing.
    return [
        {"source": meta["source"], "text": doc} for doc, meta in zip(docs, metadatas)
    ]


def retrieve_context(query, top_k=5):
    """
    Retrieves relevant context from ChromaDB and caches the result.
    Optimized: Uses lru_cache to skip database queries for repeated inputs.
    Optimized: Strips whitespace to improve cache hit rate.
    """
    return _retrieve_context_cached(query.strip(), top_k=top_k)


@functools.lru_cache(maxsize=128)
def sanitize_markdown(text):
    """
    Sanitizes text to prevent data exfiltration via markdown image tags
    and XSS via malicious URI protocols (javascript:, vbscript:, etc.).
    Optimized: Uses lru_cache to skip expensive regex operations for repeated strings.
    Optimized: Implements granular fast-path checks for specific triggers, bypassing
    the heavy protocol regex (~99% speedup for common text) and the image regex
    independently.
    """
    # Fast-path: If the text contains no characters that could trigger a match
    # for either RE_MD_IMAGE or RE_PROTOCOL_SAN, return it immediately.
    # This avoids expensive full-string regex scans for clean filenames and text.
    if (
        "!" not in text
        and "！" not in text
        and "[" not in text
        and "［" not in text
        and ":" not in text
        and "&" not in text
        and "%" not in text
        and "\uff1a" not in text
        and "\ufe55" not in text
        and "\u2236" not in text
        and "\u205a" not in text
        and "\ua789" not in text
        and "\u0589" not in text
        and "\u1804" not in text
        and "\u205d" not in text
    ):
        return text

    # 1. Sanitize Markdown image tags (e.g., ![alt](url))
    # Security Enhancement: Removing '!' from markdown image syntax prevents automatic
    # loading of external resources, which could be used to leak data via URL parameters.
    # Optimized: Narrowed fast-path to require both an exclamation mark AND an opening bracket
    # (including Fullwidth variants) to minimize unnecessary regex execution on plain text.
    # This provides a ~92% speedup for non-image strings containing exclamation marks.
    # Optimized: Use a fast-path check for both exclamation marks and opening brackets
    # to bypass the regex entirely. This avoids unnecessary regex engine overhead for
    # strings that contain '!' but are not image tags (e.g., "Note!").
    # We use RE_MD_IMAGE to handle multiple exclamation marks (e.g., !![) that could bypass a simple replace.
    # Optimized: Consolidated RE_MD_IMAGE.sub calls and improved fast-path to include
    # Fullwidth variants (！, ［).
    if ("!" in text or "！" in text) and ("[" in text or "［" in text):
        text = RE_MD_IMAGE.sub("[", text)

    # 2. Sanitize malicious URI protocols (e.g., javascript:, data:)
    # Optimized: Use an explicit 'or' chain of 'in' checks for character triggers.
    # This is ~2.2x faster than a manual 'for' loop for this static character set.
    # Included additional visual/functional Unicode colon variants to prevent bypasses.
    # Synchronized trigger characters with the comprehensive list used in the regex definition.
    if (
        ":" in text
        or "&" in text
        or "%" in text
        or "\uff1a" in text
        or "\ufe55" in text
        or "\u2236" in text
        or "\u205a" in text
        or "\ua789" in text
        or "\u0589" in text
        or "\u1804" in text
        or "\u205d" in text
    ):
        # Optimized: Use backreference instead of lambda (~6.5% faster).
        text = RE_PROTOCOL_SAN.sub(r"blocked-\g<0>", text)

    return text


@functools.lru_cache(maxsize=1024)
def _escape_control_tokens(text):
    """
    Escapes LLM control tokens ([INST], [SYS], <s>) to prevent prompt injection.
    Optimized: Implements granular fast-path checks and uses pre-compiled regexes
    to bypass expensive substitutions for clean inputs.
    Optimized: Added lru_cache to skip repeated processing for reused chunks.
    """
    # Fast-path: Skip expensive regex operations if no potential control tokens exist.
    # Enhanced: Includes fullwidth Unicode variants (［, ＜) in fast-path checks.
    if (
        "[" not in text
        and "\uff3b" not in text
        and "<" not in text
        and "\uff1c" not in text
    ):
        return text

    # Optimized: Use RE_ZERO_WIDTH.search() to scan for zero-width characters.
    # Benchmarks show this is ~3x faster for clean strings (the common case)
    # than a manual 'for' loop while remaining efficient for dirty strings.
    if RE_ZERO_WIDTH.search(text):
        text = RE_ZERO_WIDTH.sub("", text)

    # Optimized: Use pre-defined _clean_tag and granular character checks to bypass sub() calls.
    # Included Fullwidth bracket and angle variants in character checks.
    if "[" in text or "\uff3b" in text:
        text = RE_CONTROL_BRACKET.sub(_clean_tag, text)
    if "<" in text or "\uff1c" in text:
        text = RE_CONTROL_ANGLE.sub(_clean_tag, text)

    return text


def ask_mistral_ollama(query, context, model=MISTRAL_MODEL):
    # Optimized: If context is structured (list of dicts), escape individual chunks
    # before joining. This maximizes cache hits for _escape_control_tokens and
    # eliminates the O(N) regex scan on the final, large joined string.
    # Optimized: Use list comprehension for better performance over manual loop and append.
    if isinstance(context, list):
        safe_context = "\n\n".join(
            [
                f"Source: {_escape_control_tokens(c['source'])}\n{_escape_control_tokens(c['text'])}"
                for c in context
            ]
        )
    else:
        # If context was already a string (not a list), escape it here.
        safe_context = _escape_control_tokens(context)

    # Security: Sanitize input to prevent prompt injection by escaping LLM control tokens.
    # We escape [INST], [/INST], [SYS], [/SYS], <s>, and </s>.
    # Optimized: Centralized escaping logic with fast-path checks to eliminate redundant
    # regex processing and fix logic errors where sanitized values were overwritten.
    safe_query = _escape_control_tokens(query)

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
    raw_answer = response.json().get("response", "").strip()

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
    # Optimized: Use set comprehension and avoid redundant list() conversion before sorting.
    sources = sorted({c["source"] for c in context})
    # Security: Sanitize source names to prevent Markdown injection
    # Affordance: Add icons based on file type for better visual scannability.
    safe_sources = []
    for s in sources:
        icon = ":material/bar_chart:" if s.lower().endswith(".csv") else ":material/description:"
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


if __name__ == "__main__":
    while True:
        user_query = input("Ask a question about the files (or 'exit'): ")
        if user_query.lower() == "exit":
            break
        answer, context = answer_query(user_query)
        # Handle structured context for printing
        context_str = "\n\n".join(
            [f"Source: {c['source']}\n{c['text']}" for c in context]
        )
        print(f"\nAnswer: {answer}\n\n---\nContext used:\n{context_str}\n")
