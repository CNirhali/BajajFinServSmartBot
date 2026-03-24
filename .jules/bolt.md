## 2024-05-24 - Optimizing Ingestion and UI Responsiveness
**Learning:** Spawning a subprocess for ingestion in a Streamlit app is extremely inefficient because it forces re-loading of heavy ML models (e.g., SentenceTransformer) which takes ~5-10 seconds.
**Action:** Always refactor standalone ingestion scripts into callable functions that can accept pre-loaded models from the main app's session or module state.

**Learning:** `df.iterrows()` in Pandas is a significant bottleneck for row-wise processing.
**Action:** Use `df.to_dict('records')` or vectorized operations for much faster data transformation.

**Learning:** Streamlit reruns the entire script on every interaction.
**Action:** Use `@st.cache_data` for expensive data processing (like CSV parsing/merging) and `st.form` to batch user inputs and reduce unnecessary reruns.

## 2025-02-17 - Parallelizing PDF Ingestion
**Learning:** Sequential PDF parsing using `PyPDF2` is CPU-bound and becomes a bottleneck as the number of documents grows.
**Action:** Use `concurrent.futures.ProcessPoolExecutor` to parallelize document parsing across multiple CPU cores to significantly reduce ingestion time.

## 2025-05-15 - Connection Pooling for API Calls
**Learning:** Re-establishing TCP connections for every LLM API call (e.g., to Ollama) adds significant latency, especially in chat applications with multiple turns.
**Action:** Use `requests.Session()` to enable connection pooling for consecutive API requests, reducing the overhead of repeated handshakes.

## 2025-05-16 - Eliminating Redundant Operations
**Learning:** Redundant API calls (even to localhost) and redundant resource-intensive processing (like re-indexing) on every Streamlit rerun significantly degrade user experience and waste CPU/Network resources.
**Action:** Use `st.session_state` to track the state of expensive operations (e.g., file indexing) and ensure that LLM API calls using connection pooling do not have redundant standalone `requests.post` calls preceding them.

## 2025-05-17 - Lazy Loading Heavy ML Models
**Learning:** Loading heavy ML models like `SentenceTransformer` at the module level causes a massive delay (e.g., ~17s) every time the module is imported. In Streamlit, which frequently reruns or can restart, this makes the app feel extremely sluggish.
**Action:** Move heavy imports and model instantiation into a getter function (singleton pattern) to defer loading until the model is actually needed. This reduces initial import time significantly (from ~17s to ~1.6s).

## 2025-05-18 - Compounding Import Latency
**Learning:** In a Streamlit environment, importing multiple modules that each have heavy dependencies (e.g., `pandas`, `chromadb`, `PyPDF2`) at the top level leads to compounding startup and rerun latency. Even if one module is optimized, others can still cause multi-second delays.
**Action:** Apply lazy loading patterns across all utility modules (`bot.py`, `data_ingest.py`) to ensure the main `app.py` remains responsive. Moving all heavy imports into their respective usage scopes reduced the combined import time from ~9.5s to ~0.17s.

## 2025-05-19 - Vector Database and Embedding Optimizations
**Learning:** Row-by-row deletion in ChromaDB (fetching IDs first) is significantly slower and more memory-intensive than using `delete_collection()`. Additionally, modern ML libraries (SentenceTransformers) and vector databases (ChromaDB) handle NumPy arrays natively; converting them to Python lists via `.tolist()` introduces unnecessary CPU and memory overhead.
**Action:** Use `chroma_client.delete_collection()` for clearing datasets and pass NumPy embeddings directly to the database. Implement `functools.lru_cache` for query embeddings to eliminate redundant model inference for repeated queries, which reduced retrieval latency by ~56%.

## 2025-05-20 - Multi-Level RAG Caching
**Learning:** In RAG applications, the same or similar questions are often asked repeatedly (e.g., via "Quick Start" suggestions). Redundantly performing embedding, vector search, and LLM inference for these queries is a massive waste of resources and adds unnecessary latency.
**Action:** Implement `functools.lru_cache` at multiple levels: query embedding, context retrieval, and the final LLM response. This reduces the latency of repeated queries from seconds to milliseconds (~0.005s). Always provide a `clear_caches()` mechanism and trigger it in the UI (e.g., `app.py`) whenever the underlying knowledge base is modified to ensure data consistency.

## 2025-05-21 - CSV Chunk Aggregation and Cache Normalization
**Learning:** Storing every CSV row as a separate vector in a RAG system leads to database bloat and inefficient retrieval. Grouping rows into larger chunks (e.g., ~500 chars) reduces the vector count by ~90% while providing better context for time-series queries. Additionally, LRU caches are sensitive to whitespace; normalizing queries with `.strip()` before caching significantly improves hit rates for user inputs.
**Action:** Batch CSV rows into larger chunks during ingestion and wrap cached retrieval functions with query normalization logic.

## 2025-05-22 - Incremental Indexing for RAG
**Learning:** Re-indexing an entire knowledge base for every change is an $O(N)$ operation that becomes a major bottleneck as the dataset grows. Ingestion time for even small datasets can exceed 30 seconds due to embedding generation.
**Action:** Implement incremental indexing by: 1) Using stable IDs (`filename_index`); 2) Identifying new vs already-indexed files by querying database metadata; 3) Using `collection.upsert()` for updates; and 4) Deleting stale records for files no longer on disk. This reduces ingestion time for unchanged datasets from ~30s to ~0.06s (~99% speedup).

## 2025-05-23 - Batch Operations in ChromaDB
**Learning:** Performing deletions in a loop for multiple sources is inefficient and creates unnecessary database round-trips. ChromaDB's `delete` method supports complex filters, allowing for batch operations.
**Action:** Use the `$in` operator in the `where` clause (e.g., `where={"source": {"$in": list(stale_sources)}}`) to delete multiple sources in a single call, improving cleanup performance during incremental indexing.

## 2025-05-24 - Optimized Source Discovery and Client Reuse
**Learning:** Retrieving all metadatas in ChromaDB just to find unique source names is extremely slow ($O(N)$ data transfer). Since chunks use a stable `filename_index` ID format, fetching only IDs (`include=[]`) and parsing them is ~22x faster (e.g., ~0.11s vs ~0.005s) as it avoids deserializing metadata JSON for every chunk.
**Action:** Use `include=[]` in `collection.get()` for source discovery and parse filenames from IDs.

**Learning:** Initializing separate ChromaDB clients in different modules (e.g., `bot.py` and `data_ingest.py`) creates redundant connection overhead and can lead to persistence issues or "database locked" errors in some environments.
**Action:** Centralize client and collection access in a single getter (e.g., `bot.get_collection()`) and reuse it across the application. Use `chromadb.PersistentClient` for faster, more reliable persistence in modern ChromaDB.

## 2025-05-25 - Directory Scanning and Process Overhead
**Learning:**  is significantly faster (~65%) than  for large or frequently scanned directories because it avoids creating intermediate lists of paths and returns iterator-friendly objects.
**Action:** Use  for internal file scanners, especially those called on every UI interaction or rerun in Streamlit.

**Learning:**  has a non-negligible overhead (~1.5s). Parallelizing a single CPU-bound task (like parsing one PDF) is actually slower than sequential execution.
**Action:** Implement conditional parallelization: only spawn process pools when multiple independent heavy tasks are present.

## 2025-05-25 - Directory Scanning and Process Overhead
**Learning:** `os.scandir` is significantly faster (~65%) than `glob.glob` for large or frequently scanned directories because it avoids creating intermediate lists of paths and returns iterator-friendly objects.
**Action:** Use `os.scandir` for internal file scanners, especially those called on every UI interaction or rerun in Streamlit.

**Learning:** `ProcessPoolExecutor` has a non-negligible overhead (~1.5s). Parallelizing a single CPU-bound task (like parsing one PDF) is actually slower than sequential execution.
**Action:** Implement conditional parallelization: only spawn process pools when multiple independent heavy tasks are present.

## 2026-03-18 - Incremental UI State and CSV Caching in Streamlit
**Learning:** Streamlit reruns trigger expensive string operations (like `df.to_csv().encode()`) and $O(N)$ reconstructions of export logs even if the underlying data hasn't changed. As chat history or dataset size grows, this creates a palpable lag in UI responsiveness.
**Action:** Cache CSV conversions using `@st.cache_data` and maintain an incrementally updated "export string" in `st.session_state` instead of re-building it from the full history on every rerun. This ensures constant-time performance for sidebars and download buttons.

## 2025-05-26 - Pre-calculating UI Metadata in Streamlit
**Learning:** In Streamlit, any logic placed directly in the main rendering loop (like parsing chat history to generate labels) is executed on every user interaction. As history grows, this $O(N \times M)$ processing becomes a significant bottleneck.
**Action:** Pre-calculate all UI-specific metadata (e.g., formatted source labels, sanitized queries) at the time of data creation and store it alongside the data in `st.session_state`. This reduces the rendering loop to a simple $O(N)$ display task.

## 2026-03-18 - UI Context Pre-processing in Streamlit
**Learning:** Rendering complex RAG context (grouping chunks by source, sanitizing names, adding icons) in the Streamlit rendering loop leads to $O(N \times M)$ overhead that compounds as chat history grows. Even with cached retrieval, the UI processing itself becomes a bottleneck.
**Action:** Pre-group, sanitize, and format the entire RAG context into a `ui_context` object (list of pre-formatted source blocks) at message creation. The rendering loop should only iterate and display these static blocks, ensuring constant-time UI updates regardless of document complexity.

## 2026-03-22 - Regex Backreferences and Overhead Reduction
**Learning:** In Python, using a callable (lambda or function) in `re.sub` is significantly slower than using a string template with backreferences (e.g., `\g<0>`, `\g<name>`) because it incurs the cost of a Python function call for every match.
**Action:** Prefer string templates and named capturing groups in `re.sub` for performance-critical text processing. Replacing a lambda with backreferences for LLM tag escaping yielded a ~51% speedup in benchmarks.

**Learning:** Redundant calls to `os.path.basename` or similar string/path utilities inside tight loops (like PDF chunking) add unnecessary overhead that scales with document size.
**Action:** Pre-calculate constant values (like filenames or sanitization results) outside loops to minimize $O(N)$ overhead.

## 2026-03-23 - Caching Pure String Utilities
**Learning:** Pure functions that perform regex-based string sanitization (like `sanitize_markdown`) are often called repeatedly on the same inputs (e.g., filenames in UI loops or common user queries). Even if they are fast individually (~0.1ms), the cumulative overhead during Streamlit's frequent reruns adds up.
**Action:** Use `functools.lru_cache` for pure string utility functions. This reduced the time for 100 calls on a 10k character string from ~0.49s to ~0.005s in benchmarks, ensuring the UI remains snappy regardless of content complexity.
