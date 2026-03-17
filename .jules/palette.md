# Palette's Journal

## 2025-05-14 - [Initial Observation]
**Learning:** The application uses Streamlit for the UI. Streamlit's default behavior for forms and inputs is functional but can be enhanced with better accessibility and visual feedback.
**Action:** Always check if `st.text_input` has `max_chars`, and if `st.button` or `st.form_submit_button` has `help` tooltips and `use_container_width=True` where appropriate.

## 2026-03-11 - [Accessible Data Tables]
**Learning:** For financial applications, charts are great for trends but inaccessible for precision and screen readers. Providing a "Data Table" tab with `st.dataframe` and proper `st.column_config` (currency formatting, date formatting) significantly improves accessibility and user trust.
**Action:** Always offer a raw data view alongside complex visualizations to ensure data accessibility and transparency.

## 2025-05-15 - [Engaging Empty States]
**Learning:** In chat-based interfaces, the "empty state" is a prime opportunity to demonstrate the assistant's personality. Using an actual `st.chat_message("assistant")` block to welcome users and provide guided suggestions is far more engaging and intuitive than a static info box or toast.
**Action:** Always prefer interactive, themed components for empty states to set the right tone for the user session.
