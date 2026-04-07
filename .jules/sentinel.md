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

## 2026-03-26 - [XSS Bypass via Non-Breaking Spaces in Protocol Sanitization]
**Vulnerability:** XSS protocol filters can be bypassed using various representations of Non-Breaking Spaces (NBSP), such as `&nbsp;`, `&#160;`, `&#xA0;`, or URL-encoded `%C2%A0` (e.g., `j&nbsp;avascript:`).
**Learning:** Standard whitespace filters often miss NBSP characters, which many browsers ignore or treat as whitespace within URI schemes. This allows a dangerous protocol to remain functional while evading filters that only check for literal spaces or common control characters.
**Prevention:** Extend the `gap_pattern` in protocol sanitization regexes to include NBSP in all its common forms (named entity, decimal/hex entities, and UTF-8 URL encoding). Additionally, expand the protocol blocklist to include less common but dangerous schemes like `filesystem:`, `view-source:`, and `jar:`.

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

## 2026-03-20 - [Robust Protocol Sanitization and HTML Entity Bypasses]
**Vulnerability:** XSS bypasses in Markdown protocol neutralization using various HTML entity representations (hex, decimal, padded, and case-insensitive hex).
**Learning:** Simple character maps or literal checks for dangerous protocols like `javascript:` are easily bypassed. Attackers can use `&#x41;` (uppercase hex), `&#097;` (padded decimal), or `&#x0061;` (padded hex) for any character in the protocol name. Furthermore, the colon itself can be represented as `&colon;`, `&#x3a;`, etc.
**Prevention:** Use a dynamically generated, robust regex that accounts for all variations of every character in blocked protocols. This includes literal characters (case-insensitive), decimal entities with optional zero-padding, and hex entities with optional zero-padding and case-insensitive 'x' and hex digits.

## 2026-03-21 - [Bypassing Robust Protocol Sanitization via Semicolon Omission and Encoded Gaps]
**Vulnerability:** Even complex regex-based protocol filters can be bypassed if they strictly require semicolons for HTML entities (e.g., `&#58;`) or only account for literal whitespace between characters. Browsers often parse entities without semicolons (e.g., `&#58`) and support encoded whitespace/control characters (e.g., `&#10;`, `&#x0A;`) injected into the protocol string.
**Learning:** Sanitization regexes must account for the high permissiveness of browser HTML parsers. A character in a protocol name can be represented by multiple entity variations, many of which don't require a terminating semicolon. Furthermore, "gaps" between characters can contain not just literal whitespace but also encoded control characters.
**Prevention:** Update regex generators to make semicolons optional (`;?`) in all HTML entity patterns. Define a `gap_pattern` that includes both literal whitespace/control characters (`[\s\x00-\x1F]`) and their decimal/hex HTML entity equivalents, and use this pattern as the joiner for protocol characters and before the colon.

## 2026-03-22 - [XSS Bypass via URL Encoding and Unicode Colons]
**Vulnerability:** XSS protocol filters can be bypassed using URL-encoded obfuscation (e.g., `j%0Aavascript:`) or non-standard Unicode colon variants (e.g., Fullwidth `：` and Small `﹕`) that some browsers or downstream parsers might treat as delimiters.
**Learning:** Security filters must account for the multiple layers of decoding that data might undergo. URL-encoded characters in a protocol name can bypass literal or entity-based checks. Additionally, many Unicode characters visually resemble or are functionally equivalent to the ASCII colon and must be neutralized.
**Prevention:** Extend protocol sanitization regexes to include URL-encoded variants (`%09`, `%0a`, `%0d`, `%20`) in character "gaps" and explicitly block common Unicode colon variations (`\uff1a`, `\ufe55`) in addition to ASCII and HTML-encoded colons.

## 2026-03-23 - [XSS Bypass via Named HTML Entities in Protocol Sanitization]
**Vulnerability:** Protocol filters can be bypassed using named HTML entities like `&Tab;` and `&NewLine;` (e.g., `j&Tab;avascript:`) which many browsers interpret as whitespace or ignore entirely within URI schemes.
**Learning:** Even when a regex accounts for decimal and hex HTML entities, attackers can leverage a browser's support for named entities to inject whitespace or control characters into protocol names. These named entities (e.g., `&Tab;`, `&NewLine;`) are often parsed as whitespace, allowing the protocol to execute while evading literal or numeric-entity-based filters.
**Prevention:** Extend the `gap_pattern` in protocol sanitization regexes to explicitly include common named HTML entities for whitespace and control characters, ensuring they are treated as obfuscation and correctly neutralized.

## 2026-03-25 - [XSS Bypass via Backslash Escapes in Protocol Sanitization]
**Vulnerability:** XSS protocol filters can be bypassed using backslash escapes (e.g., `j\avascript:`) which some Markdown or HTML parsers might ignore or strip before processing the URI, effectively reassembling the dangerous protocol.
**Learning:** Even with robust handling of HTML entities and URL encoding, simple literal backslashes can be used for obfuscation. Many downstream parsers are extremely permissive and will treat `j\a\v\a\s\c\r\i\p\t:` as `javascript:`.
**Prevention:** Include the literal backslash character (`\\`) in the `gap_pattern` of the protocol sanitization regex to ensure it is treated as obfuscation and correctly neutralized regardless of where it appears in the protocol name.

## 2025-05-15 - [LLM Control Token Obfuscation with Whitespace]
**Vulnerability:** Prompt injection filters that use exact string matching or strict regexes for LLM control tokens (e.g., `[INST]`, `<s>`) can be bypassed by injecting whitespace within the tags (e.g., `[ INST ]`, `<  s  >`).
**Learning:** Some LLM tokenizers or template engines are permissive and will treat tags with internal whitespace as valid control tokens, while simple security filters might miss them.
**Prevention:** Always use whitespace-aware regexes (`\s*`) when matching LLM control tokens for sanitization. Additionally, ensure the replacement string effectively "breaks" the token (e.g., by adding a space before the tag name) to prevent it from being reconstructed as a single lexical unit by the LLM's tokenizer.

## 2026-03-27 - [XSS and Prompt Injection Bypass via Unicode Zero-Width Characters]
**Vulnerability:** Security filters for URI protocols and LLM control tokens can be bypassed using Unicode zero-width characters (e.g., `\u200b`, `\u200c`, `\u200d`, `\ufeff`) which are invisible but prevent exact string matches. These can be injected even within tag names (e.g., `[I\u200bNST]`).
**Learning:** Browsers and LLM tokenizers often ignore these characters, reassembling the malicious string after it passes the filter. Standard `\s` regex patterns do not capture these characters.
**Prevention:** Extend "gap" patterns in regexes to include `\u200b-\u200f` and `\ufeff`. For control tokens, construct regexes that permit these gaps between *every* character of the tag name. As an additional layer of defense, explicitly strip these zero-width characters from untrusted input before processing.

## 2026-03-30 - [Hardening Path Traversal and Obfuscated Bypasses]
**Vulnerability:** Path traversal bypasses on Linux using Windows-style backslashes, Log Injection via CRLF characters in user-controlled metadata, and filter bypasses using directional formatting or invisible Unicode formatters.
**Learning:**
1. `os.path.basename` on Linux does not recognize `\` as a directory separator, allowing `..\..\app.py` to remain unchanged and potentially cause path traversal if not normalized.
2. Audit logs that include unsanitized user strings (like filenames) are susceptible to Log Injection, where an attacker can forge log entries by injecting newline characters.
3. Security filters for protocols and LLM control tokens must account for a wider range of invisible/format Unicode characters (beyond just zero-width spaces) such as directional embeddings and word joiners, which many parsers ignore.
**Prevention:**
1. Always normalize backslashes to forward slashes before calling `os.path.basename` for cross-platform path sanitization.
2. Implement a centralized `sanitize_log` function to strip CRLF characters from all strings before they are written to audit logs.
3. Expand "gap" patterns in security regexes to include directional formatting (`\u202a-\u202e`) and invisible formatters (`\u2060-\u206f`).

## 2025-05-15 - [Hardening URI Sanitization against Protocol Bypasses and Unicode Obfuscation]
**Vulnerability:** XSS and malicious URI execution via missing dangerous protocols (e.g., `intent:`, `ms-appinstaller:`) and obfuscated colons using visual/functional Unicode equivalents (e.g., Ratio `∶` \u2236, Two Dot Punctuation `⁚` \u205A).
**Learning:**
1. Blocklists for URI protocols must be comprehensive and include platform-specific schemes like `intent:` (Android) and `ms-appinstaller:` (Windows), which can lead to remote code execution or unauthorized app interactions.
2. Attackers can bypass protocol filters by using Unicode characters that browsers or downstream handlers treat as equivalent to the ASCII colon (`:`).
3. Named HTML entities for whitespace (e.g., `&thinsp;`, `&zwnj;`) can bypass gap filters that only account for literal whitespace or numeric entities.
**Prevention:**
1. Regularly audit and expand the URI protocol blocklist with modern and platform-specific dangerous schemes.
2. Extend protocol sanitization regexes to include functional Unicode colon variants and common named HTML entities for whitespace and control characters.
3. Ensure fast-path checks in sanitization logic are updated to include all new trigger characters (like `&` and specific Unicode variants) to avoid accidental bypasses.

## 2026-04-05 - [Control Token Bypass via Fullwidth Unicode Brackets]
**Vulnerability:** LLM control token filters (e.g., `[INST]`, `<s>`) can be bypassed using Fullwidth Unicode variants of brackets and angles (e.g., `［`, `］`, `＜`, `＞`).
**Learning:** Browsers and some LLM tokenizers may treat these Unicode variants (U+FF3B, U+FF3D, U+FF1C, U+FF1E) as equivalent to their ASCII counterparts, allowing an attacker to inject instructions that bypass standard string or regex filters.
**Prevention:** Extend control token regexes to include Fullwidth Unicode brackets and angles. Ensure that fast-path checks and normalization logic in sanitization helpers (like `_clean_tag`) are also aware of these variants to provide comprehensive coverage.
## 2026-04-01 - [Hardening Security Filters against Unicode Fullwidth Variants]
**Vulnerability:** XSS and Prompt Injection bypasses via Unicode Fullwidth homoglyphs (e.g., `！`, `［`, `］`, `＜`, `＞`) and visual/functional Unicode colon variants (e.g., `꞉` \ua789, `᠄` \u1804).
**Learning:** Security filters that strictly target ASCII characters are susceptible to bypasses using Unicode characters that browsers or LLM tokenizers treat as visually or functionally equivalent to structural markers (like brackets or colons).
**Prevention:** Extend security regexes and fast-path string checks to include Fullwidth and other visual homoglyphs for all structural characters used in markdown and LLM templates. Implement normalization in replacement logic to ensure these variants are converted to safe representations.

## 2025-05-15 - [Security Regression via Function Shadowing]
**Vulnerability:** A robust LLM control token sanitization function (`_escape_control_tokens`) was completely neutralized by a weak stub implementation appended to the end of `bot.py`.
**Learning:** In Python, if a function is defined multiple times in the same module, the last definition silently overrides all previous ones. This can be used (intentionally or accidentally) to bypass critical security filters while the "secure" code remains visible earlier in the file.
**Prevention:** Regularly audit the codebase for duplicate function or variable definitions. Use linting tools that detect shadowed names. Ensure that security-critical functions are protected and that the final exported version is the intended one.

## 2026-04-07 - [Greedy Regex Pitfalls in Sanitization Filters]
**Vulnerability:** Security filters using greedy "gap" patterns (e.g., `gap*`) before optional capture groups (e.g., `(?P<slash>[/／\\]?)`) can fail to capture variant slashes if the gap pattern also includes the slash character (like backslash).
**Learning:** In `_build_control_token_regex`, the `GAP_PATTERN` was updated to include backslashes (`\\`). When matching an obfuscated tag like `[\USER]`, the greedy `gap*` would consume the backslash, leaving the `slash` capture group empty. This prevented the intended normalization of variant slashes in the helper function.
**Prevention:** Use non-greedy quantifiers (`*?`) for gap patterns that precede optional security-critical capture groups to ensure specific variants are correctly captured and normalized rather than being "swallowed" by the general gap filter.
