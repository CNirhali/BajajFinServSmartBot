## 2024-05-24 - [Form Wrapping for Better Accessibility]
**Learning:** In Streamlit, wrapping input fields and buttons in `st.form` is essential for allowing users to submit via the "Enter" key, which is a standard accessibility expectation.
**Action:** Always prefer `st.form` for authentication and search inputs.

## 2024-05-24 - [Confirmation for Destructive Actions]
**Learning:** For long-running or destructive actions like re-indexing, a simple button click can be too easy to trigger accidentally. A confirmation checkbox adds a safety layer.
**Action:** Use a disabled state on buttons until a confirmation checkbox is checked for high-impact actions.
