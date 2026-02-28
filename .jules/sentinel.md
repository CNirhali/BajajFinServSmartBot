## 2025-05-15 - [Securing Streamlit Applications]
**Vulnerability:** Path Traversal via `st.file_uploader`, Stored XSS via `st.markdown(unsafe_allow_html=True)`, and Hardcoded Secrets.
**Learning:**
1. Streamlit's `file_uploader` provides a `name` attribute that can be manipulated if the server uses it to save files without sanitization.
2. Even with `os.path.basename`, saving to the root directory is dangerous (RCE risk by overwriting app.py).
3. `unsafe_allow_html=True` is a common source of XSS.
4. Hardcoded secrets should be removed entirely, not just moved to `os.getenv` with the secret as a default.
**Prevention:**
1. Always use `os.path.basename()` and enforce a dedicated, non-root directory for file uploads (e.g., `uploads/`).
2. Use environment variables for secrets and fail securely if they are missing.
3. Prefer Streamlit's built-in colored text markdown over raw HTML.
## 2024-05-15 - Hardcoded Authentication and Path Traversal Risks
**Vulnerability:** Hardcoded password in source code and unsanitized file uploads allowing arbitrary file writes.
**Learning:** Initial application development prioritized functionality over security, leading to the use of a hardcoded string for a simple login mechanism and direct use of user-provided filenames.
**Prevention:** Use environment variables for sensitive configuration like passwords and always sanitize filenames using `os.path.basename()` or similar before using them in file operations. Additionally, avoid `unsafe_allow_html=True` in Streamlit to prevent potential XSS from untrusted data in the future.
