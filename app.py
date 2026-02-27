import streamlit as st
import bot
from data_ingest import run_ingestion
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
    with st.form("login_form"):
        pw = st.text_input("Enter password to access the SmartBot:", type="password")
        login_submit = st.form_submit_button("Login")
        if login_submit:
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
        # Optimized: Call function directly and share embedding model to save ~5-10s startup/loading time
        run_ingestion(model=bot.embedder)
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
        # Optimized: Call function directly and share embedding model
        run_ingestion(model=bot.embedder)
    st.success("Re-indexing complete! You can now ask questions about the new files.")

st.markdown("---")

# --- Analytics Section ---
st.markdown("## 📊 BFS & Sensex Price Trends")

@st.cache_data(show_spinner=False)
def get_analytics_data(bfs_path, sensex_path):
    """Cached function to process CSV data for analytics, improving UI responsiveness."""
    try:
        bfs_df = pd.read_csv(bfs_path)
        sensex_df = pd.read_csv(sensex_path)

        # Normalise column names (strip spaces)
        bfs_df.columns = [c.strip() for c in bfs_df.columns]
        sensex_df.columns = [c.strip() for c in sensex_df.columns]

        bfs_df["Date"] = pd.to_datetime(bfs_df["Date"], errors="coerce")
        sensex_df["Date"] = pd.to_datetime(sensex_df["Date"], errors="coerce")

        # Clean BFS closing price: strip spaces, remove thousands commas, convert to float
        bfs_df["Closing_Price"] = (
            bfs_df["Closing_Price"]
            .astype(str)
            .str.replace(",", "", regex=False)
            .str.replace('"', "", regex=False)
            .str.strip()
        )
        bfs_df["Closing_Price"] = pd.to_numeric(bfs_df["Closing_Price"], errors="coerce")

        # Ensure Sensex close is numeric
        sensex_df["Close"] = pd.to_numeric(sensex_df["Close"], errors="coerce")

        merged = pd.merge(
            bfs_df[["Date", "Closing_Price"]].rename(columns={"Closing_Price": "BFS Close"}),
            sensex_df[["Date", "Close"]].rename(columns={"Close": "Sensex Close"}),
            on="Date",
            how="inner",
        )

        merged = merged.dropna(subset=["Date", "BFS Close", "Sensex Close"])
        merged = merged.sort_values("Date")
        return merged
    except Exception as e:
        return e

bfs_path = os.path.join(DATA_DIR, "BFS_Daily_Closing_Price.csv")
sensex_path = os.path.join(DATA_DIR, "Sensex_Daily_Historical_Data.csv")

if os.path.exists(bfs_path) and os.path.exists(sensex_path):
    merged = get_analytics_data(bfs_path, sensex_path)
    if isinstance(merged, pd.DataFrame):
        if not merged.empty:
            st.line_chart(merged, x="Date", y=["BFS Close", "Sensex Close"])
        else:
            st.info("No overlapping, valid dates found between BFS and Sensex CSVs to plot.")
    else:
        st.warning(f"Error loading/plotting price data: {merged}")
else:
    st.info("Upload both BFS_Daily_Closing_Price.csv and Sensex_Daily_Historical_Data.csv to see price trends.")

st.markdown("---")

# --- Chat Section ---
if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = []

st.markdown("## 💬 Ask a question")
# Optimized: Using st.form for better keyboard accessibility (Enter key) and batching updates
with st.form(key="chat_form", clear_on_submit=False):
    query = st.text_input("Enter your question:", placeholder="e.g. What was the closing price of BFS on Jan 2, 2024?", key="query_input")
    submit_button = st.form_submit_button(label="Ask")

if submit_button:
    if query:
        with st.spinner("Thinking..."):
            answer, context = bot.answer_query(query)
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
