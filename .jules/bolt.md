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
