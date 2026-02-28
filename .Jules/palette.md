## 2024-05-24 - [Form Wrapping for Better Accessibility]
**Learning:** In Streamlit, wrapping input fields and buttons in `st.form` is essential for allowing users to submit via the "Enter" key, which is a standard accessibility expectation.
**Action:** Always prefer `st.form` for authentication and search inputs.

## 2024-05-24 - [Confirmation for Destructive Actions]
**Learning:** For long-running or destructive actions like re-indexing, a simple button click can be too easy to trigger accidentally. A confirmation checkbox adds a safety layer.
**Action:** Use a disabled state on buttons until a confirmation checkbox is checked for high-impact actions.
## 2025-05-15 - [Safety Pattern for Resource-Intensive Tasks]
**Learning:** For actions like 'Re-index all files' that take significant time or resources, a simple button click can lead to accidental wait times or resource consumption. Implementing a confirmation checkbox ('Safety Pattern') that enables the button provides a deliberate friction point that improves user confidence and prevents accidental triggers.
**Action:** Always implement a confirmation checkbox for destructive or resource-heavy actions in Streamlit apps, and provide a `help` tooltip to explain the reason for the friction.
