## 2024-05-24 - Optimizing Ingestion and UI Responsiveness
**Learning:** Spawning a subprocess for ingestion in a Streamlit app is extremely inefficient because it forces re-loading of heavy ML models (e.g., SentenceTransformer) which takes ~5-10 seconds.
**Action:** Always refactor standalone ingestion scripts into callable functions that can accept pre-loaded models from the main app's session or module state.

**Learning:** `df.iterrows()` in Pandas is a significant bottleneck for row-wise processing.
**Action:** Use `df.to_dict('records')` or vectorized operations for much faster data transformation.

**Learning:** Streamlit reruns the entire script on every interaction.
**Action:** Use `@st.cache_data` for expensive data processing (like CSV parsing/merging) and `st.form` to batch user inputs and reduce unnecessary reruns.
