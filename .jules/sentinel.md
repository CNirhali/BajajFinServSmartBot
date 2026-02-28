## 2024-05-15 - Hardcoded Authentication and Path Traversal Risks
**Vulnerability:** Hardcoded password in source code and unsanitized file uploads allowing arbitrary file writes.
**Learning:** Initial application development prioritized functionality over security, leading to the use of a hardcoded string for a simple login mechanism and direct use of user-provided filenames.
**Prevention:** Use environment variables for sensitive configuration like passwords and always sanitize filenames using `os.path.basename()` or similar before using them in file operations. Additionally, avoid `unsafe_allow_html=True` in Streamlit to prevent potential XSS from untrusted data in the future.
