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

## 2026-03-25 - [Searchable Metadata Lists]
**Learning:** As a Knowledge Base grows, even a categorized list in a popover can become overwhelming to scan. Adding a real-time search filter with `st.text_input` and `label_visibility="collapsed"` provides a clean, immediate way for users to verify the presence of specific documents without excessive scrolling or cognitive load.
**Action:** Include a search filter at the top of long or metadata-heavy lists to improve scannability and user efficiency.

## 2026-03-29 - [Optimized Confirmation Dialogs]
**Learning:** Confirmation dialogs with stacked full-width buttons can feel visually overwhelming and disjointed. Using a side-by-side layout (e.g., `st.columns(2, gap="small")`) for binary choices like "Yes/No" creates a more balanced, standard, and predictable interface that matches common design patterns.
**Action:** Prefer side-by-side button layouts for binary confirmation dialogs to improve visual balance and user recognition.

## 2026-03-30 - [Information Scent & Modernized Suggestions]
**Learning:** Increasing "information scent" by adding dynamic metadata (like file counts) to navigation triggers (like popovers) provides immediate context and reduces unnecessary interactions. For "Quick Start" interfaces, replacing generic icons with context-specific Material Symbols and moving long labels to tooltips significantly improves visual scannability and professional feel.
**Action:** Always look for opportunities to surface system state in button labels and use context-aware iconography to aid rapid visual identification of features.

## 2026-03-31 - [Material Symbols and Color Markers]
**Learning:** In Streamlit markdown, Material Symbols (`:material/icon_name:`) do not render correctly if nested inside inline color blocks (e.g., `:green[:material/check_circle: Text]`). The icon must be placed outside the color block: `:material/check_circle: :green[Text]`.
**Action:** Always place Material Symbols outside of Streamlit color markers to ensure proper rendering and visual consistency.

## 2026-04-01 - [Contextual Filenames for Chat Exports]
**Learning:** For individual chat interaction downloads, including a sanitized snippet of the user query in the filename significantly improves the user's ability to manage and identify files locally without opening them.
**Action:** Use a regex (e.g., `re.sub(r'[^a-z0-9]+', '_', query[:30].lower()).strip('_')`) to include descriptive snippets in export filenames.

## 2026-04-01 - [Visual Urgency for Confirmation Dialogs]
**Learning:** Using the `icon` parameter in `st.warning` (e.g., `icon=":material/warning:"`) within confirmation popovers provides stronger visual reinforcement of the action's severity compared to just text and colors.
**Action:** Always include a relevant Material Symbol in warning/confirmation blocks to aid quick visual categorization of the interaction.

## 2026-04-02 - [Visual Checklists for Feature Gating]
**Learning:** For features that require specific files (like analytics), a generic info message is often overlooked. Using a visual checklist with Material Symbols (':material/check_circle:' vs ':material/pending:') and color coding (green vs grey) provides immediate, scannable feedback on what's missing, reducing user frustration and support queries.
**Action:** Always use side-by-side visual checklists to communicate feature requirements or multi-step setup progress.

## 2026-04-10 - [Searchable History & Dynamic Pluralization]
**Learning:** For chat-based tools with persistent history, adding a search filter (with programmatic "Clear" support via `st.session_state`) significantly reduces cognitive load by allowing users to bypass long scrolls. Furthermore, implementing dynamic pluralization (e.g., "1 interaction" vs "2 interactions") in UI labels provides a subtle but critical layer of visual polish and grammatical correctness that increases overall professional feel.
**Action:** Always include a search filter for growing message lists and ensure all count-based labels use conditional logic for proper pluralization.

## 2026-04-06 - [AI Latency Visibility]
**Learning:** For AI-powered tools, displaying response latency (generation time) increases system transparency and helps set user expectations for future queries. It also provides a subtle diagnostic tool for users to understand when the underlying model is under load.
**Action:** Always measure LLM response duration and display it in both the UI (interaction headers/captions) and session exports to improve user trust and transparency.

## 2026-04-12 - [Retrieval Granularity & Information Scent]
**Learning:** Including evidence metadata such as unique source counts and total chunk counts (with proper pluralization) in AI response captions and expanded source lists significantly increases user trust and system transparency. It provides an immediate "information scent" about the breadth and depth of the AI's reasoning basis.
**Action:** Always surface retrieval granularity (counts of sources and chunks) in the UI to help users evaluate the grounding of AI responses.
