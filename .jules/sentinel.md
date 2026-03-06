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

## 2025-05-15 - Information Leakage via Exceptions and Denial of Service (DoS) Prevention
**Vulnerability:** Raw exception objects were returned to the frontend, and external API requests lacked timeouts.
**Learning:**
1. Returning raw exceptions can expose internal system details, such as file paths or library versions.
2. Unbounded requests to external services (like Ollama) can lead to resource exhaustion if the service hangs.
**Prevention:**
1. Always catch exceptions and return user-friendly, generic error messages.
2. Always implement reasonable timeouts for all external network requests.

## 2025-05-15 - Redundant Auth UI and Incomplete Prompt Sanitization
**Vulnerability:** Redundant password input fields in `app.py` (messy logic) and incomplete escaping of Mistral instruction tags in `bot.py`.
**Learning:**
1. Messy, redundant UI code in authentication flows can lead to "shadow" vulnerabilities where one input is secured but another is not.
2. For instruction-tuned models like Mistral, escaping only the *closing* tag (`[/INST]`) is insufficient; an attacker can still inject new *opening* tags (`[INST]`) to start fresh instruction blocks that the model might prioritize over the original system instructions.
**Prevention:**
1. Consolidate authentication UI into a single, clean path and enforce strict length limits (`max_chars`).
2. Always escape all structural markers of the LLM's template (both opening and closing tags) in user-provided content.
