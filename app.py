import streamlit as st
import bot
from data_ingest import run_ingestion
import os
import secrets
import shutil
import time
import io
import pandas as pd

st.set_page_config(page_title="Bajaj Finserv SmartBot", page_icon="🤖", layout="wide")

def get_document_counts():
    """Counts the number of PDF and CSV files in the knowledge base."""
    import glob
    pdf_count = 0
    csv_count = 0
    # Match data_ingest.py patterns
    for pattern in ["*.pdf", "uploads/*.pdf"]:
        pdf_count += len(glob.glob(pattern))
    for pattern in ["*.csv", "uploads/*.csv"]:
        csv_count += len(glob.glob(pattern))
    return pdf_count, csv_count

# --- Simple Authentication ---
# Use environment variable for password to avoid hardcoded secrets
# If not set, the app will require a password, but none will be valid by default
# for better security in production.
PASSWORD = os.getenv("BOT_PASSWORD")
if not PASSWORD:
    st.error("⚠️ BOT_PASSWORD environment variable is not set. Access is disabled for security.")
    st.stop()

if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if 'last_login_attempt' not in st.session_state:
    st.session_state['last_login_attempt'] = 0.0

def login():
    st.title("🔒 Bajaj Finserv SmartBot Login")
    with st.form("login_form"):
        # Security Enhancement: Added max_chars=128 to mitigate potential DoS/resource exhaustion attacks.
        # Security Enhancement: Added max_chars=128 to the password input field to mitigate
        # potential Denial of Service (DoS) and resource exhaustion attacks.
        pw = st.text_input(
            "Enter password to access the SmartBot:",
            type="password",
            placeholder="Enter password...",
            help="Please enter the access password provided by your administrator.",
            max_chars=128
        )
        login_submit = st.form_submit_button(
            "🔓 Login",
            help="Verify credentials and enter the application.",
            use_container_width=True
        )
        if login_submit:
            # Security Enhancement: Implement rate limiting on login attempts to mitigate brute-force attacks.
            current_time = time.time()
            time_since_last = current_time - st.session_state['last_login_attempt']
            st.session_state['last_login_attempt'] = current_time

            if time_since_last < 2.0:
                st.warning(f"Too many attempts. Please wait {2.0 - time_since_last:.1f} seconds.")
            elif secrets.compare_digest(pw, PASSWORD):
                st.session_state['authenticated'] = True
                st.success("Login successful! Reloading...")
                st.rerun()
            else:
                st.error("Incorrect password. Please try again.")

if not st.session_state['authenticated']:
    login()
    st.stop()

# --- Main App ---

if 'indexed_files' not in st.session_state:
    st.session_state['indexed_files'] = []

pdf_count, csv_count = get_document_counts()

st.markdown(f"""
# 🤖 Bajaj Finserv SmartBot
**Knowledge Base:** :blue[{pdf_count} PDF Documents] | :green[{csv_count} CSV Data Files]

Ask anything about the uploaded Earnings Call Transcripts, BFS, or Sensex data! 

*Powered by Mistral LLM (Ollama) + Smart Retrieval.*
""")

st.info("""
**Privacy Notice:**
This bot only uses files you upload or that are present in this folder. No online search or external data is accessed. All processing is local and private.
""")

# --- Admin Panel ---
with st.expander("⚙️ System Administration"):
    st.markdown("### 🛠️ Admin Panel")
    confirm_reindex = st.checkbox("Confirm re-indexing (Required to enable button)")
    if st.button(
        "Re-index all files (force refresh)",
        disabled=not confirm_reindex,
        help="Re-indexing is a resource-intensive task that will re-process all documents.",
        use_container_width=True
    ):
        with st.status("Re-indexing knowledge base...", expanded=True) as status:
            st.write("Searching for documents...")
            # Optimized: Call function directly and share embedding model to save ~5-10s startup/loading time
            num_chunks = run_ingestion(model=bot.get_embedder())
            st.write(f"Indexed {num_chunks} chunks.")
            status.update(label="Re-indexing complete!", state="complete", expanded=False)
        st.toast("✅ Knowledge base re-indexed successfully!", icon="🚀")

st.markdown("---")

# --- File Upload Section ---
st.markdown("## 📁 Upload new data files (PDF/CSV)")
uploaded_files = st.file_uploader(
    "Upload PDF or CSV files to add to the knowledge base:",
    type=["pdf", "csv"],
    accept_multiple_files=True,
    key="file_uploader",
    help="You can upload multiple PDF transcripts or CSV price data files. They will be automatically indexed into the bot's memory."
)

# SECURITY: Use a dedicated uploads directory to prevent overwriting app source code
DATA_DIR = "uploads"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

if uploaded_files:
    # Optimized: Only re-index if the set of uploaded files has changed to prevent redundant processing.
    current_filenames = sorted([f.name for f in uploaded_files])
    if current_filenames != st.session_state['indexed_files']:
        for uploaded_file in uploaded_files:
            # Sanitize filename to prevent path traversal
            safe_filename = os.path.basename(uploaded_file.name)
            file_path = os.path.join(DATA_DIR, safe_filename)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

        with st.status("Indexing new files...", expanded=True) as status:
            st.write("Processing uploads...")
            # Optimized: Call function directly and share embedding model
            num_chunks = run_ingestion(model=bot.get_embedder())
            st.write(f"Indexed {num_chunks} chunks.")
            status.update(label="Indexing complete!", state="complete", expanded=False)

        st.session_state['indexed_files'] = current_filenames
        st.toast("✅ Files uploaded and indexed successfully!", icon="📁")

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

        # Explicitly specify date format to avoid warnings and ensure consistent parsing
        date_format = "%d-%b-%y"
        bfs_df["Date"] = pd.to_datetime(bfs_df["Date"], format=date_format, errors="coerce")
        sensex_df["Date"] = pd.to_datetime(sensex_df["Date"], format=date_format, errors="coerce")

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
    except Exception:
        return "An error occurred while processing the financial data. Please ensure the CSV files are correctly formatted."

def find_csv(filename):
    """Checks both root and uploads directory for a CSV file."""
    root_path = os.path.join(".", filename)
    uploads_path = os.path.join(DATA_DIR, filename)
    if os.path.exists(root_path):
        return root_path
    if os.path.exists(uploads_path):
        return uploads_path
    return None

bfs_path = find_csv("BFS_Daily_Closing_Price.csv")
sensex_path = find_csv("Sensex_Daily_Historical_Data.csv")

if bfs_path and sensex_path:
    merged = get_analytics_data(bfs_path, sensex_path)
    if isinstance(merged, pd.DataFrame):
        if not merged.empty:
            tab1, tab2 = st.tabs(["📈 Price Trend", "📊 Relative Performance"])

            with tab1:
                st.markdown("### Absolute Price Comparison")
                st.line_chart(merged, x="Date", y=["BFS Close", "Sensex Close"])
                st.caption("Note: BFS and Sensex are on different scales, making BFS appear flat in this view.")

            with tab2:
                st.markdown("### Growth Performance (Indexed to 100)")
                # Calculate relative performance indexed to 100 starting from the first data point
                rel_merged = merged.copy()
                rel_merged["BFS Growth"] = (rel_merged["BFS Close"] / rel_merged["BFS Close"].iloc[0]) * 100
                rel_merged["Sensex Growth"] = (rel_merged["Sensex Close"] / rel_merged["Sensex Close"].iloc[0]) * 100

                st.line_chart(rel_merged, x="Date", y=["BFS Growth", "Sensex Growth"])
                st.info("This view shows the percentage growth of both entities starting from 100 on the earliest available date, allowing for a fair comparison of their performance.")
        else:
            st.info("No overlapping, valid dates found between BFS and Sensex CSVs to plot.")
    else:
        st.warning(merged)
else:
    st.info("Upload both BFS_Daily_Closing_Price.csv and Sensex_Daily_Historical_Data.csv to see price trends.")

st.markdown("---")

# --- Chat Section ---
if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = []

st.markdown("## 💬 Ask a question")
# Optimized: Using st.form for better keyboard accessibility (Enter key) and batching updates

# Using st.form for better keyboard accessibility (Enter key)
with st.form(key="chat_form", clear_on_submit=False):
    query = st.text_input(
        "Enter your question:",
        placeholder="e.g. What was the closing price of BFS on Jan 2, 2024?",
        key="query_input",
        max_chars=1000
    )
    submit_button = st.form_submit_button(
        label="💬 Ask Assistant",
        help="Submit your question to the AI assistant. Press Enter to submit.",
        use_container_width=True
    )

if submit_button:
    if query:
        with st.spinner("Searching transcripts and generating response..."):
            try:
                answer, context = bot.answer_query(query)
                st.session_state['chat_history'].append({
                    'query': query,
                    'answer': answer,
                    'context': context
                })
                st.toast("Response generated!", icon="💬")
            except Exception as e:
                st.error("⚠️ Assistant is temporarily unavailable. Please ensure the local LLM server (Ollama) is running.")
    else:
        st.warning("Please enter a question.")

# --- Chat History ---
st.markdown("## 🗂️ Chat History")

if not st.session_state['chat_history']:
    st.info("👋 **No questions yet!** Ask me anything about Bajaj Finserv earnings or market trends to get started.")
    st.markdown("### 💡 Quick Start Suggestions")

    suggestions = [
        ("📄 Summarize the key points from Q1 earnings call", "Summarize the key points from Q1 earnings call"),
        ("📈 Compare BFS and Sensex prices", "Compare BFS and Sensex closing prices on the same day"),
        ("🔮 What guidance was given for FY25?", "What guidance did management give for FY25?")
    ]

    cols = st.columns(len(suggestions))
    for i, (label, suggestion) in enumerate(suggestions):
        if cols[i].button(label, use_container_width=True):
            with st.spinner(f"Generating response for: {suggestion}..."):
                try:
                    answer, context = bot.answer_query(suggestion)
                    st.session_state['chat_history'].append({
                        'query': suggestion,
                        'answer': answer,
                        'context': context
                    })
                    st.toast("Response generated!", icon="💬")
                    st.rerun()
                except Exception:
                    st.error("⚠️ Assistant is temporarily unavailable. Please ensure the local LLM server (Ollama) is running.")
else:
    with st.popover("🗑️ Clear Chat History", help="Delete all messages from the current session."):
        st.warning("Are you sure you want to clear the entire chat history?")
        if st.button("Yes, clear history", type="primary", use_container_width=True):
            st.session_state['chat_history'] = []
            st.rerun()

    for i, chat in enumerate(reversed(st.session_state['chat_history'])):
        with st.chat_message("user", avatar="👤"):
            st.markdown(chat['query'])

        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(chat['answer'])

            # Dynamically count unique sources for the expander label
            source_count = len(set(line for line in chat['context'].split('\n') if line.startswith('Source:')))
            with st.expander(f"🔍 Show context from {source_count} sources", expanded=False):
                # Optimized: Group context by source for better readability
                context_lines = chat['context'].split('\n')
                current_source = None
                current_content = []

                for line in context_lines:
                    if line.startswith('Source:'):
                        # If we have accumulated content for a previous source, render it
                        if current_source and current_content:
                            st.markdown(f":blue[**{current_source}**]")
                            st.code("\n".join(current_content), language=None)
                            current_content = []
                        current_source = line
                    else:
                        if line.strip():
                            current_content.append(line)

                # Render the final source block
                if current_source and current_content:
                    st.markdown(f":blue[**{current_source}**]")
                    st.code("\n".join(current_content), language=None)
                # Download button for answer and context
                download_text = f"Question: {chat['query']}\n\nAnswer: {chat['answer']}\n\nContext:\n{chat['context']}"
                st.download_button(
                    label="📥 Download Answer & Context",
                    data=download_text,
                    file_name=f"bfs_smartbot_answer_{i+1}.txt",
                    mime="text/plain",
                    key=f"download_{i}",
                    help="Download this specific answer and its supporting context as a text file for your records."
                )
        st.markdown("---")
