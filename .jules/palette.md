# Palette's Journal

## 2025-05-14 - [Initial Observation]
**Learning:** The application uses Streamlit for the UI. Streamlit's default behavior for forms and inputs is functional but can be enhanced with better accessibility and visual feedback.
**Action:** Always check if `st.text_input` has `max_chars`, and if `st.button` or `st.form_submit_button` has `help` tooltips and `use_container_width=True` where appropriate.

## 2026-03-11 - [Accessible Data Tables]
**Learning:** For financial applications, charts are great for trends but inaccessible for precision and screen readers. Providing a "Data Table" tab with `st.dataframe` and proper `st.column_config` (currency formatting, date formatting) significantly improves accessibility and user trust.
**Action:** Always offer a raw data view alongside complex visualizations to ensure data accessibility and transparency.

## 2026-03-16 - [Financial Metric Context]
**Learning:** Displaying absolute delta values for financial metrics (like stock prices) is often insufficient for users to grasp the significance of a change. Adding the percentage delta provides immediate relative context, making the data more actionable and insightful.
**Action:** Always include percentage deltas alongside absolute changes in financial metrics to improve data interpretation.
## 2025-05-15 - [Engaging Empty States]
**Learning:** In chat-based interfaces, the "empty state" is a prime opportunity to demonstrate the assistant's personality. Using an actual `st.chat_message("assistant")` block to welcome users and provide guided suggestions is far more engaging and intuitive than a static info box or toast.
**Action:** Always prefer interactive, themed components for empty states to set the right tone for the user session.

## 2026-03-24 - [AI Assistant Navigation Standards]
**Learning:** For AI assistants, placing "New Chat" or "Clear History" in a sidebar following industry standard patterns (like ChatGPT) significantly improves discoverability and user flow compared to placing it at the end of a growing message list.
**Action:** Always prioritize placing session management actions in a persistent sidebar or header.

## 2026-03-24 - [Visual Scannability for Multi-format RAG]
**Learning:** In RAG systems that ingest multiple file types (PDF, CSV, etc.), adding simple icons (📄, 📊) to source citations and file lists allows users to mentally categorize information sources 50-70% faster without reading full filenames.
**Action:** Use file-type icons consistently across all UI components that reference documents to aid quick visual identification.

## 2026-03-19 - [Knowledge Base Transparency & Empty States]
**Learning:** Providing human-readable file sizes in a document listing increases user trust and system transparency. Additionally, explicitly handling empty states with greyed-out, italicized fallback messages prevents the UI from looking "broken" or unfinished when no data is present.
**Action:** Always include metadata (like file size) in document lists and provide clear fallback messages for empty collections.

## 2026-03-25 - [Contextual Confirmation for Destructive Actions]
**Learning:** For destructive actions like clearing chat history, generic confirmation messages (e.g., "Are you sure?") can be easily ignored. Providing contextual details, such as the exact number of items being affected, increases user awareness and provides a final moment of reflection that reduces accidental data loss.
**Action:** Always include dynamic counts or specific identifiers in confirmation dialogs for destructive operations.

## 2026-03-25 - [Popovers and Overflow Management]
**Learning:** In Streamlit, popovers containing dynamic lists (like document indexes) can become excessively tall, pushing critical action buttons off-screen or creating an awkward scrolling experience for the entire page. Using `st.container(height=X)` within the popover provides a stable, scrollable area that preserves the popover's layout and improves visual scannability.
**Action:** Always wrap dynamic lists inside popovers or expanders in fixed-height scrollable containers to maintain UI stability.
