import streamlit as st
import bot
import data_ingest
import os
import secrets
import shutil
import time
import io
import pandas as pd

st.set_page_config(page_title="Bajaj Finserv SmartBot", page_icon="🤖", layout="wide")

@st.cache_data(show_spinner=False)
def get_knowledge_base_details():
    """
    Counts and lists the PDF and CSV files in the knowledge base.
    Optimized: Uses the centralized get_knowledge_base_files scanner and caches results
    to minimize disk I/O on every Streamlit rerun.
    """
    disk_pdfs, disk_csvs = data_ingest.get_knowledge_base_files()

    pdf_files = sorted(set(os.path.basename(p) for p in disk_pdfs))
    csv_files = sorted(set(os.path.basename(p) for p in disk_csvs))

    # Calculate last updated time based on file modifications
    all_paths = disk_pdfs + disk_csvs
    last_updated = "Never"
    if all_paths:
        try:
            latest_mtime = max(os.path.getmtime(f) for f in all_paths)
            last_updated = time.strftime("%b %d, %H:%M", time.localtime(latest_mtime))
        except Exception:
            pass

    return len(pdf_files), len(csv_files), pdf_files, csv_files, last_updated


# --- Simple Authentication ---
# Use environment variable for password to avoid hardcoded secrets
# If not set, the app will require a password, but none will be valid by default
# for better security in production.
PASSWORD = os.getenv("BOT_PASSWORD")
if not PASSWORD:
    st.error(
        "⚠️ BOT_PASSWORD environment variable is not set. Access is disabled for security."
    )
    st.stop()

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if "last_login_attempt" not in st.session_state:
    st.session_state["last_login_attempt"] = 0.0

if "last_query_time" not in st.session_state:
    st.session_state["last_query_time"] = 0.0

if "last_reindex_time" not in st.session_state:
    st.session_state["last_reindex_time"] = 0.0


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
            help="Please enter the access password provided by your administrator. Press Enter to login.",
            max_chars=128,
        )
        login_submit = st.form_submit_button(
            "🔓 Login",
            help="Verify credentials and enter the application.",
            use_container_width=True,
        )
        if login_submit:
            # Security Enhancement: Implement rate limiting on login attempts to mitigate brute-force attacks.
            current_time = time.time()
            time_since_last = current_time - st.session_state["last_login_attempt"]
            st.session_state["last_login_attempt"] = current_time

            if time_since_last < 2.0:
                st.warning(
                    f"Too many attempts. Please wait {2.0 - time_since_last:.1f} seconds."
                )
            elif secrets.compare_digest(pw, PASSWORD):
                # Security: Audit logging for successful login
                print(
                    f"[AUDIT] Successful login at {time.strftime('%Y-%m-%d %H:%M:%S')}"
                )
                st.session_state["authenticated"] = True
                st.success("Login successful! Reloading...")
                time.sleep(0.5)
                st.rerun()
            else:
                # Security: Audit logging for failed login
                print(
                    f"[AUDIT] Failed login attempt at {time.strftime('%Y-%m-%d %H:%M:%S')}"
                )
                st.error("Incorrect password. Please try again.")


if not st.session_state["authenticated"]:
    login()
    st.stop()

# --- Sidebar ---
with st.sidebar:
    st.title("🛡️ Sentinel Security")
    if st.button(
        "🔒 Logout",
        help="Securely end your session and clear all temporary data.",
        use_container_width=True,
    ):
        # Security: Audit logging for logout
        print(f"[AUDIT] User logged out at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.success("Logged out successfully!")
        time.sleep(0.5)
        st.rerun()

# --- Main App ---

if "indexed_files" not in st.session_state:
    st.session_state["indexed_files"] = []

pdf_count, csv_count, pdf_files, csv_files, last_updated = get_knowledge_base_details()

st.markdown("# 🤖 Bajaj Finserv SmartBot")

h1, h2 = st.columns([0.7, 0.3])
with h1:
    st.markdown(f"""
    :grey[🟢 Assistant Ready] | :grey[🕒 Last updated: {last_updated}]

    **Knowledge Base:** :blue[{pdf_count} PDF Documents] | :green[{csv_count} CSV Data Files]

    Ask anything about the uploaded Earnings Call Transcripts, BFS, or Sensex data!
    """)
with h2:
    with st.popover(
        "📂 View indexed files",
        help="Click to see a detailed list of all documents and data files currently in the knowledge base.",
        width="stretch",
    ):
        st.markdown("### 🗂️ Indexed Files")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**📄 PDFs ({pdf_count})**")
            for f in pdf_files:
                st.caption(f"- {f}")
        with c2:
            st.markdown(f"**📊 CSVs ({csv_count})**")
            for f in csv_files:
                st.caption(f"- {f}")

st.markdown("*Powered by Mistral LLM (Ollama) + Smart Retrieval.*")

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
        help="Re-indexing is a resource-intensive task that will re-process all documents. A 60-second cooldown applies.",
        use_container_width=True,
    ):
        # Security Enhancement: Implement cooldown for resource-intensive re-indexing to prevent DoS.
        current_time = time.time()
        time_since_last = current_time - st.session_state["last_reindex_time"]
        if time_since_last < 60.0:
            st.warning(
                f"Re-indexing is on cooldown. Please wait {60.0 - time_since_last:.1f} seconds."
            )
            st.stop()

        st.session_state["last_reindex_time"] = current_time
        # Security: Audit logging for high-impact administrative actions
        print(f"[AUDIT] Re-indexing triggered at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        try:
            with st.status("Re-indexing knowledge base...", expanded=True) as status:
                st.write("Searching for documents...")
                # Optimized: Call function directly and share embedding model to save ~5-10s startup/loading time.
                # Optimized: Explicitly pass force=True to perform a full re-index as requested by the user.
                num_chunks = data_ingest.run_ingestion(model=bot.get_embedder(), force=True)
                # Optimized: Clear query and answer caches after re-indexing to ensure fresh results.
                bot.clear_caches()
                # Optimized: Clear knowledge base details cache to reflect changes in the UI.
                get_knowledge_base_details.clear()
                st.write(f"Indexed {num_chunks} chunks.")
                status.update(
                    label="Re-indexing complete!", state="complete", expanded=False
                )
        except Exception as e:
            # Security: Mask raw exception details and log to server
            print(f"[ERROR] Re-indexing failed: {e}")
            st.error(
                "⚠️ Re-indexing failed. Please check the server logs or contact your administrator."
            )
            st.stop()
        st.toast("✅ Knowledge base re-indexed successfully!", icon="🚀")

st.markdown("---")

# --- File Upload Section ---
st.markdown("## 📁 Upload new data files (PDF/CSV)")
uploaded_files = st.file_uploader(
    "Upload PDF or CSV files to add to the knowledge base:",
    type=["pdf", "csv"],
    accept_multiple_files=True,
    key="file_uploader",
    help="You can upload multiple PDF transcripts or CSV price data files (max 10MB per file). They will be automatically indexed into the bot's memory.",
)

# SECURITY: Use a dedicated uploads directory to prevent overwriting app source code
DATA_DIR = "uploads"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

if uploaded_files:
    # Security Enhancement: Limit the number of files per upload to 10 to prevent resource exhaustion.
    if len(uploaded_files) > 10:
        st.error("Too many files. Please upload a maximum of 10 files at once.")
        st.stop()

    # Optimized: Only re-index if the set of uploaded files has changed to prevent redundant processing.
    current_filenames = sorted([f.name for f in uploaded_files])
    if current_filenames != st.session_state["indexed_files"]:
        saved_filenames = []
        for uploaded_file in uploaded_files:
            # Security Enhancement: Limit file size to 10MB to prevent DoS.
            MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
            if uploaded_file.size > MAX_FILE_SIZE:
                st.error(f"Skipping {uploaded_file.name}: File exceeds 10MB limit.")
                continue

            # Security Enhancement: Robustly sanitize filename to prevent path traversal.
            # os.path.basename() alone is insufficient if the filename is '..' or '.'
            safe_filename = os.path.basename(uploaded_file.name)
            if safe_filename in [".", "..", ""]:
                st.error(f"Skipping invalid filename: {uploaded_file.name}")
                continue

            file_path = os.path.join(DATA_DIR, safe_filename)
            try:
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                saved_filenames.append(uploaded_file.name)
            except Exception as e:
                # Security: Mask raw exception details in the UI and log to server
                print(f"[ERROR] Failed to save {uploaded_file.name}: {e}")
                st.error(
                    f"Error saving {uploaded_file.name}. Please contact your administrator."
                )

        if saved_filenames:
            # Security: Audit logging for successful file uploads
            print(
                f"[AUDIT] Files uploaded: {', '.join(saved_filenames)} at {time.strftime('%Y-%m-%d %H:%M:%S')}"
            )

        try:
            with st.status("Indexing new files...", expanded=True) as status:
                st.write("Processing uploads...")
                # Optimized: Call function directly and share embedding model
                num_chunks = data_ingest.run_ingestion(model=bot.get_embedder())
                # Optimized: Clear query and answer caches after new data is added.
                bot.clear_caches()
                # Optimized: Clear knowledge base details cache to reflect uploaded files in the UI.
                get_knowledge_base_details.clear()
                st.write(f"Indexed {num_chunks} chunks.")
                status.update(
                    label="Indexing complete!", state="complete", expanded=False
                )
        except Exception as e:
            # Security: Mask raw exception details and log to server
            print(f"[ERROR] Ingestion failed: {e}")
            st.error("⚠️ Ingestion of new files failed. Please check the server logs.")
            st.stop()

        st.session_state["indexed_files"] = sorted(saved_filenames)
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
        bfs_df["Date"] = pd.to_datetime(
            bfs_df["Date"], format=date_format, errors="coerce"
        )
        sensex_df["Date"] = pd.to_datetime(
            sensex_df["Date"], format=date_format, errors="coerce"
        )

        # Clean BFS closing price: strip spaces, remove thousands commas, convert to float
        bfs_df["Closing_Price"] = (
            bfs_df["Closing_Price"]
            .astype(str)
            .str.replace(",", "", regex=False)
            .str.replace('"', "", regex=False)
            .str.strip()
        )
        bfs_df["Closing_Price"] = pd.to_numeric(
            bfs_df["Closing_Price"], errors="coerce"
        )

        # Ensure Sensex close is numeric
        sensex_df["Close"] = pd.to_numeric(sensex_df["Close"], errors="coerce")

        merged = pd.merge(
            bfs_df[["Date", "Closing_Price"]].rename(
                columns={"Closing_Price": "BFS Close"}
            ),
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
            # Calculate metrics for at-a-glance insights
            latest_bfs = merged["BFS Close"].iloc[-1]
            prev_bfs = merged["BFS Close"].iloc[-2] if len(merged) > 1 else latest_bfs
            bfs_delta = latest_bfs - prev_bfs

            latest_sensex = merged["Sensex Close"].iloc[-1]
            prev_sensex = (
                merged["Sensex Close"].iloc[-2] if len(merged) > 1 else latest_sensex
            )
            sensex_delta = latest_sensex - prev_sensex

            latest_date = merged["Date"].iloc[-1].strftime("%b %d, %Y")

            tab1, tab2, tab3 = st.tabs(
                ["📈 Price Trend", "📊 Relative Performance", "🗂️ Data Table"]
            )

            with tab1:
                st.markdown(f"### Absolute Price Comparison (as of {latest_date})")
                m1, m2 = st.columns(2)
                m1.metric(
                    "Latest BFS Close",
                    f"₹{latest_bfs:,.2f}",
                    f"{bfs_delta:+,.2f}",
                    help="Closing price of Bajaj Finserv stock and change from the previous trading session."
                )
                m2.metric(
                    "Latest Sensex Close",
                    f"{latest_sensex:,.2f}",
                    f"{sensex_delta:+,.2f}",
                    help="Closing value of the BSE Sensex and change from the previous trading session."
                )
                st.line_chart(merged, x="Date", y=["BFS Close", "Sensex Close"])
                st.caption(
                    "Note: BFS and Sensex are on different scales, making BFS appear flat in this view."
                )
                st.download_button(
                    label="📥 Download Price Data (CSV)",
                    data=merged.to_csv(index=False).encode("utf-8"),
                    file_name="bfs_sensex_prices.csv",
                    mime="text/csv",
                    help="Download the absolute price data for BFS and Sensex as a CSV file.",
                    use_container_width=True,
                )

            with tab2:
                st.markdown("### Growth Performance (Indexed to 100)")
                # Calculate relative performance indexed to 100 starting from the first data point
                rel_merged = merged.copy()
                bfs_base = rel_merged["BFS Close"].iloc[0]
                sensex_base = rel_merged["Sensex Close"].iloc[0]
                rel_merged["BFS Growth"] = (rel_merged["BFS Close"] / bfs_base) * 100
                rel_merged["Sensex Growth"] = (
                    rel_merged["Sensex Close"] / sensex_base
                ) * 100

                g1, g2 = st.columns(2)
                bfs_total_pct = ((latest_bfs / bfs_base) - 1) * 100
                sensex_total_pct = ((latest_sensex / sensex_base) - 1) * 100
                g1.metric(
                    "Total BFS Growth",
                    f"{bfs_total_pct:+.1f}%",
                    help="Overall percentage growth since the start of the dataset.",
                )
                g2.metric(
                    "Total Sensex Growth",
                    f"{sensex_total_pct:+.1f}%",
                    help="Overall percentage growth since the start of the dataset.",
                )

                st.line_chart(rel_merged, x="Date", y=["BFS Growth", "Sensex Growth"])
                st.info(
                    "This view shows the percentage growth of both entities starting from 100 on the earliest available date, allowing for a fair comparison of their performance."
                )
                st.download_button(
                    label="📥 Download Growth Data (CSV)",
                    data=rel_merged.to_csv(index=False).encode("utf-8"),
                    file_name="bfs_sensex_growth.csv",
                    mime="text/csv",
                    help="Download the relative growth performance data as a CSV file.",
                    use_container_width=True,
                )

            with tab3:
                st.markdown("### Underlying Price Data")
                st.dataframe(
                    merged,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Date": st.column_config.DateColumn(
                            "Date", format="DD MMM YYYY"
                        ),
                        "BFS Close": st.column_config.NumberColumn(
                            "BFS Close (₹)", format="₹%.2f"
                        ),
                        "Sensex Close": st.column_config.NumberColumn(
                            "Sensex Close", format="%.2f"
                        ),
                    },
                )
                st.caption(
                    "This table provides the exact values used in the visualizations above for accessibility and detailed inspection."
                )
        else:
            st.info(
                "No overlapping, valid dates found between BFS and Sensex CSVs to plot."
            )
    else:
        st.warning(merged)
else:
    st.info(
        "Upload both BFS_Daily_Closing_Price.csv and Sensex_Daily_Historical_Data.csv to see price trends."
    )

st.markdown("---")

# --- Chat Section ---
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

st.markdown("## 💬 Ask a question")
# Optimized: Using st.form for better keyboard accessibility (Enter key) and batching updates

# Using st.form for better keyboard accessibility (Enter key)
with st.form(key="chat_form", clear_on_submit=True):
    query = st.text_input(
        "Enter your question:",
        placeholder="e.g. What was the closing price of BFS on Jan 2, 2024?",
        key="query_input",
        max_chars=1000,
    )
    submit_button = st.form_submit_button(
        label="💬 Ask Assistant",
        help="Submit your question to the AI assistant. Press Enter to submit.",
        use_container_width=True,
    )

if submit_button:
    if query:
        # Security Enhancement: Implement rate limiting on queries to prevent DoS/resource exhaustion.
        current_time = time.time()
        time_since_last = current_time - st.session_state["last_query_time"]
        if time_since_last < 3.0:
            st.warning(
                f"Please wait {3.0 - time_since_last:.1f} seconds before asking another question."
            )
        else:
            st.session_state["last_query_time"] = current_time
            with st.spinner("Searching transcripts and generating response..."):
                try:
                    answer, context = bot.answer_query(query)
                    st.session_state['chat_history'].append({
                        'query': query,
                        'answer': answer,
                        'context': context,
                        'timestamp': time.strftime("%H:%M")
                    })
                    st.toast("Response generated!", icon="💬")
                except Exception as e:
                    # Security: Mask raw exception details and log to server
                    print(f"[ERROR] Chat query failed: {e}")
                    st.error(
                        "⚠️ Assistant is temporarily unavailable. Please ensure the local LLM server (Ollama) is running."
                    )
    else:
        st.warning("Please enter a question.")

# --- Chat History ---
st.markdown("## 🗂️ Chat History")

if not st.session_state["chat_history"]:
    st.info(
        "👋 **No questions yet!** Ask me anything about Bajaj Finserv earnings or market trends to get started."
    )
    st.markdown("### 💡 Quick Start Suggestions")

    suggestions = [
        (
            "📄 Summarize the key points from Q1 earnings call",
            "Summarize the key points from Q1 earnings call",
        ),
        (
            "📈 Compare BFS and Sensex prices",
            "Compare BFS and Sensex closing prices on the same day",
        ),
        (
            "🔮 What guidance was given for FY25?",
            "What guidance did management give for FY25?",
        ),
    ]

    cols = st.columns(len(suggestions))
    for i, (label, suggestion) in enumerate(suggestions):
        if cols[i].button(
            label,
            use_container_width=True,
            help="Click to ask this question instantly.",
        ):
            # Security Enhancement: Implement rate limiting on queries to prevent DoS/resource exhaustion.
            current_time = time.time()
            time_since_last = current_time - st.session_state["last_query_time"]
            if time_since_last < 3.0:
                st.warning(
                    f"Too many requests. Please wait {3.0 - time_since_last:.1f} seconds."
                )
            else:
                st.session_state["last_query_time"] = current_time
                with st.spinner(f"Generating response for: {suggestion}..."):
                    try:
                        answer, context = bot.answer_query(suggestion)
                        st.session_state['chat_history'].append({
                            'query': suggestion,
                            'answer': answer,
                            'context': context,
                            'timestamp': time.strftime("%H:%M")
                        })
                        st.toast("Response generated!", icon="💬")
                        st.rerun()
                    except Exception as e:
                        # Security: Mask raw exception details and log to server
                        print(f"[ERROR] Quick start suggestion failed: {e}")
                        st.error(
                            "⚠️ Assistant is temporarily unavailable. Please ensure the local LLM server (Ollama) is running."
                        )
else:
    with st.popover(
        "🗑️ Clear Chat History", help="Delete all messages from the current session."
    ):
        st.warning("Are you sure you want to clear the entire chat history?")
        if st.button(
            "🗑️ Yes, clear history",
            type="primary",
            use_container_width=True,
            help="Confirm deletion of all chat history.",
        ):
            st.session_state["chat_history"] = []
            st.rerun()

    for i, chat in enumerate(reversed(st.session_state['chat_history'])):
        ts = chat.get('timestamp', '')
        with st.chat_message("user", avatar="👤"):
            st.markdown(chat['query'])
            if ts:
                st.caption(f"Sent at {ts}")

        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(chat['answer'])
            if ts:
                st.caption(f"Response at {ts}")

            # Dynamically extract and format unique source names for the expander label
            sources = sorted(
                list(
                    set(
                        line.replace("Source:", "").strip()
                        for line in chat["context"].split("\n")
                        if line.startswith("Source:")
                    )
                )
            )
            source_names = ", ".join(sources)
            # Truncate source names if they are too long for the label
            if len(source_names) > 60:
                source_names = source_names[:57] + "..."

            expander_label = f"🔍 Show context from {len(sources)} sources"
            if sources:
                expander_label += f": {source_names}"

            with st.expander(expander_label, expanded=False):
                # Optimized: Group context by source for better readability
                context_lines = chat["context"].split("\n")
                current_source = None
                current_content = []

                for line in context_lines:
                    if line.startswith("Source:"):
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
                    help="Download this specific answer and its supporting context as a text file for your records.",
                )
        st.markdown("---")
