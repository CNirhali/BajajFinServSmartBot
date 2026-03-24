import streamlit as st
try:
    # Test text_input with icon
    st.text_input("test", icon=":material/search:")
    print("st.text_input(icon=...) is supported")
except TypeError as e:
    print(f"st.text_input(icon=...) failed: {e}")

try:
    # Test form_submit_button with shortcut
    with st.form("test_form"):
        st.form_submit_button("test", shortcut="Ctrl+Enter")
    print("st.form_submit_button(shortcut=...) is supported")
except TypeError as e:
    print(f"st.form_submit_button(shortcut=...) failed: {e}")
