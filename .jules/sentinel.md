## 2025-05-15 - [Securing Streamlit Applications]
**Vulnerability:** Path Traversal via `st.file_uploader`, Stored XSS via `st.markdown(unsafe_allow_html=True)`, and Hardcoded Secrets.
**Learning:** Streamlit's `file_uploader` provides a `name` attribute that can be manipulated if the server uses it to save files without sanitization. `unsafe_allow_html=True` is a common source of XSS in Streamlit apps and should be avoided in favor of native markdown colors like `:blue[text]`.
**Prevention:** Always use `os.path.basename()` on user-provided filenames. Use environment variables for secrets. Prefer Streamlit's built-in colored text markdown over raw HTML.
