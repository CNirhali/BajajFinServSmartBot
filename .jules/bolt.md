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
