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

## 2025-05-15 - Brute-Force Mitigation in Streamlit
**Vulnerability:** Lack of rate limiting on the login form allowed for unlimited rapid-fire password guessing attempts.
**Learning:** Streamlit applications are often targeted by brute-force attacks due to their interactive nature. Traditional backend rate limiting might be missing in simple deployments.
**Prevention:** Implement session-based rate limiting using `st.session_state` to track and enforce a cooldown (e.g., 2 seconds) between sensitive actions like authentication attempts.

## 2026-03-11 - [Defense-in-Depth for LLM Output and Exception Masking]
**Vulnerability:** Potential XSS via LLM-generated `javascript:` links and information leakage via unhandled Streamlit exceptions.
**Learning:**
1. LLMs can be manipulated to generate malicious markdown links using the `javascript:` protocol. Neutralizing this protocol case-insensitively (`re.IGNORECASE`) is a necessary layer of defense.
2. Streamlit's default behavior is to show raw exception traces in the UI, which leaks internal system state. Catching all top-level exceptions in interactive components and replacing them with generic messages is essential for production security.
**Prevention:**
1. Always sanitize LLM output for known XSS vectors like `javascript:` and `data:` URI schemes.
2. Implement global or component-level try-except blocks in Streamlit that log the raw error to server stdout but show a safe message to the user.

## 2025-05-15 - [Markdown Sanitization & Filename Validation]
**Vulnerability:** XSS via stored user queries and exfiltration via file/resource URI protocols. Potential DoS via long filenames.
**Learning:**
1. Sanitizing LLM output is not enough; user-provided content rendered back to the UI (e.g., chat history) must also be sanitized for markdown-based exfiltration and XSS.
2. Modern browsers support dangerous URI schemes like `file:` and `resource:` that must be neutralized alongside `javascript:`.
3. Unvalidated filename lengths can cause filesystem errors or resource exhaustion.
**Prevention:**
1. Shared sanitization utilities should be used for all untrusted markdown rendering (user and assistant).
2. Protocol blocklists should include local and browser-internal schemes.
3. Implement strict length limits (e.g., 255 chars) on all user-controlled filenames.

## 2026-03-15 - [UI Markdown Injection and LLM Runaway Mitigation]
**Vulnerability:** Potential Markdown injection via file/source names and resource exhaustion from unbounded LLM responses.
**Learning:**
1. Any UI component that supports Markdown (like Streamlit's `st.caption`) is an injection vector if it displays untrusted data like filenames.
2. Even with `timeout` and `max_chars` on input, a malicious or malfunctioning LLM can still trigger a DoS by generating an extremely long response.
**Prevention:**
1. Sanitize ALL untrusted data before rendering in Markdown-capable UI components, including metadata like filenames.
2. Always enforce response length limits (e.g., `num_predict` in Ollama) at the LLM API level.
