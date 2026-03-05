## 2024-05-24 - [Form Wrapping for Better Accessibility]
**Learning:** In Streamlit, wrapping input fields and buttons in `st.form` is essential for allowing users to submit via the "Enter" key, which is a standard accessibility expectation.
**Action:** Always prefer `st.form` for authentication and search inputs.

## 2024-05-24 - [Confirmation for Destructive Actions]
**Learning:** For long-running or destructive actions like re-indexing, a simple button click can be too easy to trigger accidentally. A confirmation checkbox adds a safety layer.
**Action:** Use a disabled state on buttons until a confirmation checkbox is checked for high-impact actions.
## 2025-05-15 - [Safety Pattern for Resource-Intensive Tasks]
**Learning:** For actions like 'Re-index all files' that take significant time or resources, a simple button click can lead to accidental wait times or resource consumption. Implementing a confirmation checkbox ('Safety Pattern') that enables the button provides a deliberate friction point that improves user confidence and prevents accidental triggers.
**Action:** Always implement a confirmation checkbox for destructive or resource-heavy actions in Streamlit apps, and provide a `help` tooltip to explain the reason for the friction.

## 2025-05-15 - [Grouped Progress Feedback with st.status]
**Learning:** For complex, multi-step background tasks like document indexing, using `st.status` provides a more transparent and professional user experience than a generic spinner. It allows users to see individual progress steps and their outcomes within a single, collapsible component.
**Action:** Use `st.status` for long-running tasks that involve multiple logical steps (e.g., searching, parsing, embedding).

## 2025-05-15 - [Delightful Chat with Avatars]
**Learning:** Adding consistent avatars to chat messages significantly improves the visual hierarchy and personality of a chatbot interface, making it easier for users to distinguish between their inputs and the assistant's responses at a glance.
**Action:** Always include appropriate avatars in `st.chat_message` to enhance user engagement and visual clarity.

## 2025-05-15 - [Cohesive Context Rendering for Better Readability]
**Learning:** Displaying RAG (Retrieval-Augmented Generation) context line-by-line in separate UI components (like `st.code` blocks) creates significant visual noise and fragmentation. Grouping context by source and rendering it in a single, cohesive block per source significantly improves readability and makes the interface feel more professional.
**Action:** Group RAG context by source and render within a single cohesive component per source in the 'Show context' expander.

## 2025-05-16 - [Streamlit Configuration and Progressive Disclosure]
**Learning:** `st.set_page_config` MUST be the first Streamlit command executed; if it's placed after other UI elements (like in a conditional login block), the app will error or fail to apply branding to the initial view. Additionally, using `st.expander` for administrative tools ("progressive disclosure") significantly reduces cognitive load for the average user while keeping high-impact actions accessible.
**Action:** Always place `st.set_page_config` at the top of the main script and use `st.expander` to declutter the interface from secondary or expert-level controls.
