import streamlit as st
from bot import answer_query
import os
import shutil
import time
import io
import pandas as pd

# --- Simple Authentication ---
PASSWORD = "bajajgpt2024"  # Change this to your desired password
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

def login():
    st.title("🔒 Bajaj Finserv SmartBot Login")
    pw = st.text_input("Enter password to access the SmartBot:", type="password")
    if st.button("Login"):
        if pw == PASSWORD:
            st.session_state['authenticated'] = True
            st.success("Login successful! Reloading...")
            st.rerun()
        else:
            st.error("Incorrect password. Please try again.")

if not st.session_state['authenticated']:
    login()
    st.stop()

# --- Main App ---
st.set_page_config(page_title="Bajaj Finserv SmartBot", page_icon="🤖", layout="wide")

st.markdown("""
# 🤖 Bajaj Finserv SmartBot

Ask anything about the uploaded Earnings Call Transcripts, BFS, or Sensex data! 

*Powered by Mistral LLM (Ollama) + Smart Retrieval.*
""")

st.info("""
**Privacy Notice:**
This bot only uses files you upload or that are present in this folder. No online search or external data is accessed. All processing is local and private.
""")

# --- Admin Panel ---
st.markdown("## 🛠️ Admin Panel")
if st.button("Re-index all files (force refresh)"):
    st.info("Re-indexing knowledge base. Please wait...")
    with st.spinner("Re-indexing files..."):
        import subprocess
        subprocess.run(["python", "data_ingest.py"])  # Re-ingest all files
        time.sleep(2)
    st.success("Re-indexing complete! You can now ask questions about the new files.")

st.markdown("---")

# --- File Upload Section ---
st.markdown("## 📁 Upload new data files (PDF/CSV)")
uploaded_files = st.file_uploader(
    "Upload PDF or CSV files to add to the knowledge base:",
    type=["pdf", "csv"],
    accept_multiple_files=True,
    key="file_uploader"
)

DATA_DIR = "."

if uploaded_files:
    for uploaded_file in uploaded_files:
        file_path = os.path.join(DATA_DIR, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.success(f"Uploaded {uploaded_file.name}")
    st.info("Re-indexing knowledge base. Please wait...")
    with st.spinner("Re-indexing files..."):
        import subprocess
        subprocess.run(["python", "data_ingest.py"])  # Re-ingest all files
        time.sleep(2)
    st.success("Re-indexing complete! You can now ask questions about the new files.")

st.markdown("---")

# --- Analytics Section ---
st.markdown("## 📊 BFS & Sensex Price Trends")
bfs_path = os.path.join(DATA_DIR, 'BFS_Daily_Closing_Price.csv')
sensex_path = os.path.join(DATA_DIR, 'Sensex_Daily_Historical_Data.csv')
if os.path.exists(bfs_path) and os.path.exists(sensex_path):
    try:
        bfs_df = pd.read_csv(bfs_path)
        sensex_df = pd.read_csv(sensex_path)
        # Try to parse date columns
        for df in [bfs_df, sensex_df]:
            for col in df.columns:
                if 'date' in col.lower():
                    df[col] = pd.to_datetime(df[col], errors='coerce')
        # Try to find closing price columns
        bfs_close_col = next((c for c in bfs_df.columns if 'close' in c.lower()), None)
        sensex_close_col = next((c for c in sensex_df.columns if 'close' in c.lower()), None)
        bfs_date_col = next((c for c in bfs_df.columns if 'date' in c.lower()), None)
        sensex_date_col = next((c for c in sensex_df.columns if 'date' in c.lower()), None)
        if bfs_close_col and sensex_close_col and bfs_date_col and sensex_date_col:
            merged = pd.merge(
                bfs_df[[bfs_date_col, bfs_close_col]].rename(columns={bfs_date_col: 'Date', bfs_close_col: 'BFS Close'}),
                sensex_df[[sensex_date_col, sensex_close_col]].rename(columns={sensex_date_col: 'Date', sensex_close_col: 'Sensex Close'}),
                on='Date', how='inner'
            )
            merged = merged.sort_values('Date')
            st.line_chart(merged.set_index('Date'))
        else:
            st.info("Could not auto-detect date/close columns in CSVs.")
    except Exception as e:
        st.warning(f"Error loading/plotting price data: {e}")
else:
    st.info("Upload both BFS_Daily_Closing_Price.csv and Sensex_Daily_Historical_Data.csv to see price trends.")

st.markdown("---")

# --- Chat Section ---
if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = []

st.markdown("## 💬 Ask a question")
query = st.text_input("Enter your question:", placeholder="e.g. What was the closing price of BFS on Jan 2, 2024?", key="query")

if st.button("Ask") or (query and st.session_state.get('last_query') != query):
    if query:
        with st.spinner("Thinking..."):
            answer, context = answer_query(query)
        st.session_state['last_query'] = query
        st.session_state['chat_history'].append({
            'query': query,
            'answer': answer,
            'context': context
        })
    else:
        st.warning("Please enter a question.")

# --- Chat History ---
st.markdown("## 🗂️ Chat History")
for i, chat in enumerate(reversed(st.session_state['chat_history'])):
    st.markdown(f"**Q{i+1}:** {chat['query']}")
    st.markdown(f"**📝 Answer:** {chat['answer']}")
    with st.expander("Show context used for answer", expanded=False):
        # Highlight source in context
        context_lines = chat['context'].split('\n')
        for line in context_lines:
            if line.startswith('Source:'):
                st.markdown(f"<span style='color: #1f77b4; font-weight: bold'>{line}</span>", unsafe_allow_html=True)
            else:
                st.code(line, language=None)
        # Download button for answer and context
        download_text = f"Question: {chat['query']}\n\nAnswer: {chat['answer']}\n\nContext:\n{chat['context']}"
        st.download_button(
            label="Download Answer & Context as Text",
            data=download_text,
            file_name=f"bfs_smartbot_answer_{i+1}.txt",
            mime="text/plain"
        )
    st.markdown("---")

st.markdown("""
<sub>Tip: Try complex queries like *'Summarize the key points from Q1 earnings call'*, *'Compare BFS and Sensex closing prices on the same day'*, or *'What guidance did management give for FY25?'*</sub>
""", unsafe_allow_html=True) 