import streamlit as st
import bot
import data_ingest
import os
import secrets
import time
import math
import re
import pandas as pd
from collections import defaultdict

st.set_page_config(page_title="Bajaj Finserv SmartBot", page_icon="🤖", layout="wide")


def sanitize_log(text):
    """
    Sanitizes user-provided text for use in audit logs to prevent log injection.
    Removes newline and carriage return characters.
    """
    if not isinstance(text, str):
        text = str(text)
    return text.replace("\n", " ").replace("\r", " ")


def format_size(size_bytes):
    """Converts bytes to human-readable format."""
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB")

    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"


@st.cache_data(show_spinner=False)
def convert_df_to_csv(df):
    """
    Caches the CSV-encoded bytes of a DataFrame to avoid redundant $O(N)$
    string conversion and encoding during Streamlit reruns.
    Security Enhancement: Sanitizes DataFrame content to prevent CSV Injection.
    """
    # Defensive copy to avoid modifying the original DataFrame in session state
    safe_df = df.copy()

    # Prepend a single quote to any cell starting with a dangerous character.
    # This prevents spreadsheet applications from interpreting the cell as a formula.
    # Dangerous characters: =, +, -, @, \t, \r
    # Optimized: Use vectorized Pandas string methods on 'object' columns instead of per-cell .apply().
    # This provides a ~2.3x speedup on medium-sized datasets (e.g. 120k rows) and avoids
    # redundant checks on numeric or boolean columns.
    dangerous_chars = ("=", "+", "-", "@", "\t", "\r")

    for col in safe_df.select_dtypes(include=["object"]).columns:
        # Use vectorized str.startswith with the tuple of dangerous characters
        mask = safe_df[col].str.startswith(dangerous_chars, na=False)
        if mask.any():
            # Prepend the single quote only to matching rows using vectorized concatenation
            safe_df.loc[mask, col] = "'" + safe_df.loc[mask, col].astype(str)

    return safe_df.to_csv(index=False).encode("utf-8")


@st.cache_data(show_spinner=False)
def get_knowledge_base_details():
    """
    Counts and lists the PDF and CSV files in the knowledge base.
    Optimized: Uses the centralized get_knowledge_base_files scanner and caches results
    to minimize disk I/O on every Streamlit rerun.
    Optimized: Uses pre-calculated metadata from get_knowledge_base_files to avoid
    redundant stat() and basename() calls.
    """
    disk_pdfs, disk_csvs = data_ingest.get_knowledge_base_files()
    total_bytes = 0
    latest_mtime = 0

    pdf_files = []
    # Sort by filename
    for f_meta in sorted(disk_pdfs, key=lambda x: x["name"]):
        # Optimized: Pre-sanitize the filename within the cached function.
        # Uses pre-calculated name and size.
        safe_name = bot.sanitize_markdown(f_meta["name"])
        pdf_files.append({"name": safe_name, "size": format_size(f_meta["size"])})
        total_bytes += f_meta["size"]
        if f_meta["mtime"] > latest_mtime:
            latest_mtime = f_meta["mtime"]

    csv_files = []
    for f_meta in sorted(disk_csvs, key=lambda x: x["name"]):
        # Optimized: Pre-sanitize the filename within the cached function.
        # Uses pre-calculated name and size.
        safe_name = bot.sanitize_markdown(f_meta["name"])
        csv_files.append({"name": safe_name, "size": format_size(f_meta["size"])})
        total_bytes += f_meta["size"]
        if f_meta["mtime"] > latest_mtime:
            latest_mtime = f_meta["mtime"]

    # Calculate last updated time
    last_updated = "Never"
    if latest_mtime > 0:
        last_updated = time.strftime("%b %d, %H:%M", time.localtime(latest_mtime))

    return (
        len(pdf_files),
        len(csv_files),
        pdf_files,
        csv_files,
        last_updated,
        format_size(total_bytes),
    )


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
            "Enter password to access the SmartBot: :red[*]",
            type="password",
            placeholder="Enter password...",
            help="Please enter the access password provided by your administrator. Press Enter to login.",
            max_chars=128,
            icon=":material/password:",
        )
        login_submit = st.form_submit_button(
            "Login",
            help="Verify credentials and enter the application. Press Enter to submit.",
            width="stretch",
            icon=":material/login:",
            shortcut="Enter",
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
    st.title("🛡️ Session Management")

    # UX Enhancement: Move Clear Chat to sidebar as "New Chat" for better accessibility
    chat_history = st.session_state.get("chat_history", [])
    history_count = len(chat_history)
    int_text = "interaction" if history_count == 1 else "interactions"
    if "history_search_input" not in st.session_state:
        st.session_state["history_search_input"] = ""

    with st.popover(
        f"New Chat ({history_count})",
        help="Clear the current conversation and start a new session.",
        width="stretch",
        icon=":material/delete_sweep:",
    ):
        st.warning(
            f"Are you sure you want to clear all {history_count} {int_text}?",
            icon=":material/warning:",
        )
        c1, c2 = st.columns(2, gap="small")
        if c1.button(
            "Yes, clear",
            type="primary",
            width="stretch",
            help="Confirm deletion of all chat history.",
            icon=":material/delete_forever:",
        ):
            st.session_state["chat_history"] = []
            # Optimized: Clear the cached export text as well.
            st.session_state["full_export_text"] = (
                "=== Bajaj Finserv SmartBot Session Export ===\n\n"
            )
            st.toast("Chat history cleared!", icon=":material/delete_sweep:")
            time.sleep(0.5)
            st.rerun()
        if c2.button(
            "No, keep",
            width="stretch",
            help="Return to the chat without clearing history.",
            icon=":material/undo:",
        ):
            # Streamlit rerun resets the popover state, effectively closing it.
            st.rerun()

    st.markdown("---")
    st.markdown("### 📥 Session Export")
    if chat_history:
        # Optimized: Use pre-calculated export text from session state to avoid O(N) reconstruction on every rerun.
        export_text = st.session_state.get(
            "full_export_text", "=== Bajaj Finserv SmartBot Session Export ===\n\n"
        )
        st.download_button(
            label=f"Download Full Conversation ({history_count} {int_text})",
            data=st.session_state["full_export_text"],
            file_name=f"smartbot_session_{time.strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain",
            help="Download all interactions from this session as a text file.",
            width="stretch",
            icon=":material/download:",
        )
        st.caption("💡 Tip: You can download your entire session history above for offline review.")
    else:
        st.info("No chat history to download yet.", icon=":material/history_toggle_off:")

    st.markdown("---")
    with st.popover(
        "Logout",
        help="Securely end your session and clear all temporary data.",
        width="stretch",
        icon=":material/logout:",
    ):
        st.warning(
            f"Are you sure you want to logout? This will clear all {history_count} {int_text} from your current session.",
            icon=":material/warning:",
        )
        c1, c2 = st.columns(2, gap="small")
        if c1.button(
            "Yes, Logout",
            type="primary",
            width="stretch",
            help="Confirm logout and clear session.",
            icon=":material/logout:",
        ):
            # Security: Audit logging for logout
            print(f"[AUDIT] User logged out at {time.strftime('%Y-%m-%d %H:%M:%S')}")
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.success("Logged out successfully!")
            time.sleep(0.5)
            st.rerun()
        if c2.button(
            "No, stay",
            width="stretch",
            help="Return to the application without logging out.",
            icon=":material/cancel:",
        ):
            st.rerun()

# --- Main App ---

if "indexed_files" not in st.session_state:
    st.session_state["indexed_files"] = []

(
    pdf_count,
    csv_count,
    pdf_files,
    csv_files,
    last_updated,
    total_size_str,
) = get_knowledge_base_details()

st.markdown("# 🤖 Bajaj Finserv SmartBot")

h1, h2 = st.columns([0.7, 0.3])
with h1:
    st.markdown(f"""
    :material/check_circle: :green[Assistant Ready] | :material/history: :grey[Last updated: {last_updated}]

    **Knowledge Base:** :blue[{pdf_count} PDFs] | :green[{csv_count} CSVs] | :orange[{total_size_str} total]

    Ask anything about the uploaded Earnings Call Transcripts, BFS, or Sensex data!
    """)
with h2:
    with st.popover(
        f"View indexed files ({pdf_count + csv_count})",
        help="Click to see a detailed list of all documents and data files currently in the knowledge base.",
        width="stretch",
        icon=":material/inventory_2:",
    ):
        st.markdown("### :material/folder_managed: Indexed Files")
        search_term = st.text_input(
            "Search indexed files",
            placeholder="Search filenames...",
            icon=":material/search:",
            label_visibility="collapsed",
            key="kb_search",
        ).lower()

        filtered_pdfs = [f for f in pdf_files if search_term in f["name"].lower()]
        filtered_csvs = [f for f in csv_files if search_term in f["name"].lower()]

        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**:material/description: PDFs ({len(filtered_pdfs)}/{pdf_count})**")
            with st.container(height=200):
                if not filtered_pdfs:
                    if search_term:
                        st.caption(":grey[*No matching PDFs found*]")
                    else:
                        st.caption(":grey[*No PDF documents indexed*]")
                for f in filtered_pdfs:
                    # Optimized: Filename is already sanitized in get_knowledge_base_details.
                    st.caption(f":material/description: {f['name']} :grey[({f['size']})]")
        with c2:
            st.markdown(f"**:material/bar_chart: CSVs ({len(filtered_csvs)}/{csv_count})**")
            with st.container(height=200):
                if not filtered_csvs:
                    if search_term:
                        st.caption(":grey[*No matching CSVs found*]")
                    else:
                        st.caption(":grey[*No CSV data files indexed*]")
                for f in filtered_csvs:
                    # Optimized: Filename is already sanitized in get_knowledge_base_details.
                    st.caption(f":material/bar_chart: {f['name']} :grey[({f['size']})]")

st.markdown("*Powered by Mistral LLM (Ollama) + Smart Retrieval.*")

st.info("""
**Privacy Notice:**
This bot only uses files you upload or that are present in this folder. No online search or external data is accessed. All processing is local and private.
""", icon=":material/privacy_tip:")

# --- Admin Panel ---
with st.expander("⚙️ System Administration"):
    st.markdown("### 🛠️ Admin Panel")
    confirm_reindex = st.checkbox(
        "Confirm re-indexing (Required to enable button)",
        help="Re-indexing is a heavy operation. Please confirm you want to proceed.",
    )
    if st.button(
        "Re-index all files (force refresh)",
        disabled=not confirm_reindex,
        help="Re-indexing is a resource-intensive task that will re-process all documents. A 60-second cooldown applies.",
        width="stretch",
        icon=":material/refresh:",
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
                num_chunks = data_ingest.run_ingestion(
                    model=bot.get_embedder(), force=True
                )
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
            # Security Enhancement: Use sanitize_log to prevent Log Injection.
            print(sanitize_log(f"[ERROR] Re-indexing failed: {e}"))
            st.error(
                "⚠️ Re-indexing failed. Please check the server logs or contact your administrator."
            )
            st.stop()
        st.toast("✅ Knowledge base re-indexed successfully!", icon=":material/rocket_launch:")

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
            # Replace backslashes with forward slashes to ensure os.path.basename works correctly
            # on all platforms (especially Linux containers receiving Windows-style paths).
            # os.path.basename() alone is insufficient if the filename is '..' or '.'
            safe_filename = os.path.basename(uploaded_file.name.replace("\\", "/"))
            if safe_filename in [".", "..", ""]:
                st.error(f"Skipping invalid filename: {uploaded_file.name}")
                continue

            # Security Enhancement: Backend extension check to prevent unauthorized file types.
            if not safe_filename.lower().endswith((".pdf", ".csv")):
                st.error(
                    f"Skipping {uploaded_file.name}: Only PDF and CSV files are allowed."
                )
                continue

            # Security Enhancement: Limit filename length to prevent filesystem-related issues or DoS.
            if len(safe_filename) > 255:
                st.error(
                    f"Skipping {uploaded_file.name}: Filename exceeds 255 character limit."
                )
                continue

            file_path = os.path.join(DATA_DIR, safe_filename)
            try:
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                saved_filenames.append(uploaded_file.name)
            except Exception as e:
                # Security: Mask raw exception details in the UI and log to server
                # Security Enhancement: Use sanitize_log to prevent Log Injection.
                print(sanitize_log(f"[ERROR] Failed to save {uploaded_file.name}: {e}"))
                st.error(
                    f"Error saving {uploaded_file.name}. Please contact your administrator."
                )

        if saved_filenames:
            # Security Enhancement: Sanitize filename list to prevent Log Injection.
            safe_filenames_str = sanitize_log(", ".join(saved_filenames))
            # Security: Audit logging for successful file uploads
            print(
                f"[AUDIT] Files uploaded: {safe_filenames_str} at {time.strftime('%Y-%m-%d %H:%M:%S')}"
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
            # Security Enhancement: Use sanitize_log to prevent Log Injection.
            print(sanitize_log(f"[ERROR] Ingestion failed: {e}"))
            st.error("⚠️ Ingestion of new files failed. Please check the server logs.")
            st.stop()

        st.session_state["indexed_files"] = sorted(saved_filenames)
        st.toast("✅ Files uploaded and indexed successfully!", icon=":material/cloud_done:")

st.markdown("---")

# --- Analytics Section ---
st.markdown("## :material/analytics: BFS & Sensex Price Trends")


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
            bfs_pct_delta = (bfs_delta / prev_bfs * 100) if prev_bfs != 0 else 0

            latest_sensex = merged["Sensex Close"].iloc[-1]
            prev_sensex = (
                merged["Sensex Close"].iloc[-2] if len(merged) > 1 else latest_sensex
            )
            sensex_delta = latest_sensex - prev_sensex
            sensex_pct_delta = (
                (sensex_delta / prev_sensex * 100) if prev_sensex != 0 else 0
            )

            latest_date = merged["Date"].iloc[-1].strftime("%b %d, %Y")

            tab1, tab2, tab3 = st.tabs(
                [":material/trending_up: Price Trend", ":material/bar_chart: Relative Performance", ":material/table_view: Data Table"]
            )

            with tab1:
                st.markdown(f"### Absolute Price Comparison (as of {latest_date})")
                m1, m2 = st.columns(2)
                m1.metric(
                    "Latest BFS Close",
                    f"₹{latest_bfs:,.2f}",
                    f"{bfs_delta:+,.2f} ({bfs_pct_delta:+,.2f}%)",
                    help="Closing price of Bajaj Finserv stock and change from the previous trading session.",
                )
                m2.metric(
                    "Latest Sensex Close",
                    f"{latest_sensex:,.2f}",
                    f"{sensex_delta:+,.2f} ({sensex_pct_delta:+,.2f}%)",
                    help="Closing value of the BSE Sensex and change from the previous trading session.",
                )
                st.line_chart(merged, x="Date", y=["BFS Close", "Sensex Close"])
                st.caption(
                    "Note: BFS and Sensex are on different scales, making BFS appear flat in this view."
                )
                # Optimized: Use cached CSV encoding to avoid redundant O(N) conversion.
                st.download_button(
                    label="Download Price Data (CSV)",
                    data=convert_df_to_csv(merged),
                    file_name="bfs_sensex_prices.csv",
                    mime="text/csv",
                    help="Download the absolute price data for BFS and Sensex as a CSV file.",
                    width="stretch",
                    icon=":material/download:",
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
                # Optimized: Use cached CSV encoding to avoid redundant O(N) conversion.
                st.download_button(
                    label="Download Growth Data (CSV)",
                    data=convert_df_to_csv(rel_merged),
                    file_name="bfs_sensex_growth.csv",
                    mime="text/csv",
                    help="Download the relative growth performance data as a CSV file.",
                    width="stretch",
                    icon=":material/download:",
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
        "To unlock price trends and performance analytics, please ensure both historical CSV files are present in the knowledge base.",
        icon=":material/analytics:",
    )
    c1, c2 = st.columns(2)
    with c1:
        if bfs_path:
            st.markdown(":material/check_circle: :green[**BFS_Daily_Closing_Price.csv**]")
        else:
            st.markdown(":material/pending: :grey[BFS_Daily_Closing_Price.csv]")
    with c2:
        if sensex_path:
            st.markdown(":material/check_circle: :green[**Sensex_Daily_Historical_Data.csv**]")
        else:
            st.markdown(":material/pending: :grey[Sensex_Daily_Historical_Data.csv]")
    st.caption(
        "💡 **Tip:** You can upload these files in the section above. The bot will automatically detect them and generate the charts."
    )

st.markdown("---")

# --- Chat Section ---
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

if "full_export_text" not in st.session_state:
    st.session_state["full_export_text"] = "=== Bajaj Finserv SmartBot Session Export ===\n\n"

st.markdown("## :material/forum: Ask a question")
# Optimized: Using st.form for better keyboard accessibility (Enter key) and batching updates

# Using st.form for better keyboard accessibility (Enter key)
with st.form(key="chat_form", clear_on_submit=True):
    query = st.text_input(
        "Enter your question:",
        placeholder="e.g. What was the closing price of BFS on Jan 2, 2024?",
        key="query_input",
        max_chars=1000,
        icon=":material/search:",
    )
    submit_button = st.form_submit_button(
        label="Ask Assistant",
        help="Submit your question to the AI assistant. Press Ctrl+Enter to submit.",
        width="stretch",
        icon=":material/chat:",
        shortcut="Ctrl+Enter",
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
                    start_time = time.perf_counter()
                    answer, context = bot.answer_query(query)
                    duration = round(time.perf_counter() - start_time, 2)
                    # Optimized: Pre-join context for download button to avoid reconstruction on every rerun.
                    context_full_text = "\n\n".join(
                        [f"Source: {c['source']}\n{c['text']}" for c in context]
                    )

                    # Optimized: Pre-calculate UI metadata (sorted sources and expander label)
                    # to eliminate redundant processing during every Streamlit rerun.
                    expander_label, _ = bot.format_source_label(context)

                    # Optimized: Group and sanitize context for UI rendering once.
                    grouped_context = defaultdict(list)
                    for item in context:
                        grouped_context[item["source"]].append(item["text"])

                    ui_context = []
                    for src in sorted(grouped_context.keys()):
                        icon = ":material/bar_chart:" if src.lower().endswith(".csv") else ":material/description:"
                        ui_context.append(
                            {
                                "source_label": f"{icon} :blue[**Source: {bot.sanitize_markdown(src)}**]",
                                "content": "\n\n".join(grouped_context[src]),
                            }
                        )

                    # Optimized: Pre-calculate the individual download text (query + answer + context)
                    # to avoid expensive string joining and formatting during interaction-triggered reruns.
                    download_text = f"Question: {query}\n\nAnswer: {answer}\n\nContext:\n{context_full_text}"

                    # Optimized: Pre-calculate sanitized query for filename to avoid redundant regex
                    # work during the rendering loop of every Streamlit rerun.
                    sanitized_query_filename = re.sub(
                        r"[^a-z0-9]+", "_", query[:30].lower()
                    ).strip("_")

                    # Optimized: Pre-calculate UI metadata and sanitize user query once before storing to history,
                    # reducing CPU overhead during subsequent UI reruns.
                    new_chat = {
                        "query": bot.sanitize_markdown(query),
                        "answer": answer,
                        "context": context,
                        "context_full_text": context_full_text,
                        "individual_download_text": download_text,
                        "sanitized_query_filename": sanitized_query_filename,
                        "expander_label": expander_label,
                        "ui_context": ui_context,
                        "timestamp": time.strftime("%H:%M"),
                        "duration": duration,
                    }
                    st.session_state["chat_history"].append(new_chat)

                    # Optimized: Incrementally update the full session export text to avoid O(N) reconstruction.
                    export_text = st.session_state.get(
                        "full_export_text",
                        "=== Bajaj Finserv SmartBot Session Export ===\n\n",
                    )
                    export_text += f"--- Interaction {len(st.session_state['chat_history'])} ---\n"
                    export_text += f"Timestamp: {new_chat['timestamp']}\n"
                    export_text += f"User: {new_chat['query']}\n"
                    export_text += f"Assistant: {new_chat['answer']}\n"
                    export_text += f"Duration: {new_chat['duration']}s\n\n"
                    st.session_state["full_export_text"] = export_text
                    st.toast("Response generated!", icon=":material/forum:")
                except Exception as e:
                    # Security: Mask raw exception details and log to server
                    # Security Enhancement: Use sanitize_log to prevent Log Injection.
                    print(sanitize_log(f"[ERROR] Chat query failed: {e}"))
                    st.error(
                        "⚠️ Assistant is temporarily unavailable. Please ensure the local LLM server (Ollama) is running."
                    )
    else:
        st.warning("Please enter a question.")

# --- Chat History ---
history_count = len(st.session_state.get("chat_history", []))

c1, c2 = st.columns([0.6, 0.4])
with c1:
    st.markdown(f"## :material/folder_managed: Chat History ({history_count})")

if st.session_state.get("chat_history"):
    with c2:
        st.text_input(
            "Search chat history",
            placeholder="Search questions or answers...",
            icon=":material/search:",
            label_visibility="collapsed",
            key="history_search_input",
        )
history_search = st.session_state.get("history_search_input", "").lower()

if not st.session_state.get("chat_history"):
    with st.chat_message("assistant", avatar=":material/smart_toy:"):
        st.markdown("""
        👋 **Welcome! I'm your Bajaj Finserv SmartBot.**

        I can help you analyze Earnings Call Transcripts and financial data. Ask me about:
        - **Key financial highlights** from recent quarters.
        - **Stock price trends** and market performance.
        - **Future guidance** and management outlook.

        To get started, try one of the suggestions below or type your own question above!
        """)

    st.markdown("### 💡 Quick Start Suggestions")

    suggestions = [
        (
            "Summarize key points...",
            "Summarize the key points from Q1 earnings call",
            ":material/summarize:",
        ),
        (
            "Compare BFS and Sensex...",
            "Compare BFS and Sensex closing prices on the same day",
            ":material/compare:",
        ),
        (
            "View FY25 guidance...",
            "What guidance did management give for FY25?",
            ":material/insights:",
        ),
    ]

    cols = st.columns(len(suggestions))
    for i, (label, suggestion, icon) in enumerate(suggestions):
        if cols[i].button(
            label,
            width="stretch",
            help=f"Ask: '{suggestion}'",
            icon=icon,
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
                        start_time = time.perf_counter()
                        answer, context = bot.answer_query(suggestion)
                        duration = round(time.perf_counter() - start_time, 2)
                        # Optimized: Pre-join context for download button.
                        context_full_text = "\n\n".join(
                            [f"Source: {c['source']}\n{c['text']}" for c in context]
                        )

                        # Optimized: Pre-calculate UI metadata (sorted sources and expander label)
                        expander_label, _ = bot.format_source_label(context)

                        # Optimized: Group and sanitize context for UI rendering once.
                        grouped_context = defaultdict(list)
                        for item in context:
                            grouped_context[item["source"]].append(item["text"])

                        ui_context = []
                        for src in sorted(grouped_context.keys()):
                            icon = ":material/bar_chart:" if src.lower().endswith(".csv") else ":material/description:"
                            ui_context.append(
                                {
                                    "source_label": f"{icon} :blue[**Source: {bot.sanitize_markdown(src)}**]",
                                    "content": "\n\n".join(grouped_context[src]),
                                }
                            )

                        # Optimized: Pre-calculate the individual download text for suggestions.
                        download_text = f"Question: {suggestion}\n\nAnswer: {answer}\n\nContext:\n{context_full_text}"

                        # Optimized: Pre-calculate sanitized query for filename.
                        sanitized_query_filename = re.sub(
                            r"[^a-z0-9]+", "_", suggestion[:30].lower()
                        ).strip("_")

                        # Optimized: Pre-calculate UI metadata and sanitize suggestion once before storing to history.
                        new_chat = {
                            "query": bot.sanitize_markdown(suggestion),
                            "answer": answer,
                            "context": context,
                            "context_full_text": context_full_text,
                            "individual_download_text": download_text,
                            "sanitized_query_filename": sanitized_query_filename,
                            "expander_label": expander_label,
                            "ui_context": ui_context,
                            "timestamp": time.strftime("%H:%M"),
                            "duration": duration,
                        }
                        st.session_state["chat_history"].append(new_chat)

                        # Optimized: Incrementally update the full session export text to avoid O(N) reconstruction.
                        export_text = st.session_state.get(
                            "full_export_text",
                            "=== Bajaj Finserv SmartBot Session Export ===\n\n",
                        )
                        export_text += f"--- Interaction {len(st.session_state['chat_history'])} ---\n"
                        export_text += f"Timestamp: {new_chat['timestamp']}\n"
                        export_text += f"User: {new_chat['query']}\n"
                        export_text += f"Assistant: {new_chat['answer']}\n"
                        export_text += f"Duration: {new_chat['duration']}s\n\n"
                        st.session_state["full_export_text"] = export_text
                        st.toast("Response generated!", icon=":material/forum:")
                        st.rerun()
                    except Exception as e:
                        # Security: Mask raw exception details and log to server
                        # Security Enhancement: Use sanitize_log to prevent Log Injection.
                        print(sanitize_log(f"[ERROR] Quick start suggestion failed: {e}"))
                        st.error(
                            "⚠️ Assistant is temporarily unavailable. Please ensure the local LLM server (Ollama) is running."
                        )
else:
    # Filter chat history if search term is provided
    if history_search:
        # Keep track of original index to maintain correct "Interaction N" numbering
        filtered_history = [
            (idx, chat)
            for idx, chat in enumerate(st.session_state["chat_history"])
            if history_search in chat["query"].lower()
            or history_search in chat["answer"].lower()
        ]
        display_history = reversed(filtered_history)
        st.caption(
            f":material/filter_list: Showing {len(filtered_history)} of {history_count} interactions matching ':blue[{history_search}]'"
        )
        if not filtered_history:
            st.info(
                "No matching interactions found. Try a different search term.",
                icon=":material/search_off:",
            )
            if st.button("Clear Search", icon=":material/close:"):
                st.session_state["history_search_input"] = ""
                st.rerun()
    else:
        display_history = reversed(list(enumerate(st.session_state["chat_history"])))

    for original_idx, chat in display_history:
        ts = chat.get("timestamp", "")
        duration = chat.get("duration")
        duration_str = f" • {duration}s" if duration else ""
        st.markdown(
            f"### :material/forum: Interaction {original_idx + 1} :grey[({ts}{duration_str})]"
        )
        with st.chat_message("user", avatar=":material/person:"):
            # Optimized: User query is already sanitized before storage.
            st.markdown(chat["query"])
            if ts:
                st.caption(f"Sent at {ts}")

        with st.chat_message("assistant", avatar=":material/smart_toy:"):
            st.markdown(chat["answer"])
            if ts:
                gen_info = f" (generated in {duration}s)" if duration else ""
                st.caption(f"Response at {ts}{gen_info}")

            # Optimized: Use pre-calculated expander label from session state
            # to avoid redundant set operations and sorting on every rerun.
            context_data = chat["context"]
            expander_label = chat.get("expander_label")

            # Fallback for old sessions if necessary
            if not expander_label:
                expander_label, _ = bot.format_source_label(context_data)

            with st.expander(expander_label, expanded=False):
                # Optimized: Use pre-calculated ui_context for efficient rendering,
                # avoiding redundant grouping, sorting, and sanitization on every rerun.
                ui_context = chat.get("ui_context")
                if ui_context:
                    for entry in ui_context:
                        st.markdown(entry["source_label"])
                        st.code(entry["content"], language=None)
                else:
                    # Fallback for old sessions if ui_context is missing
                    grouped_context = defaultdict(list)
                    for item in context_data:
                        grouped_context[item["source"]].append(item["text"])

                    for src in sorted(grouped_context.keys()):
                        icon = ":material/bar_chart:" if src.lower().endswith(".csv") else ":material/description:"
                        st.markdown(
                            f"{icon} :blue[**Source: {bot.sanitize_markdown(src)}**]"
                        )
                        st.code("\n\n".join(grouped_context[src]), language=None)

                # Download button for answer and context
                # Optimized: Use pre-calculated individual download text from session state.
                # Optimized: Use pre-calculated individual_download_text from session state
                # to avoid redundant string concatenation on every rerun.
                download_text = chat.get("individual_download_text")
                if not download_text:
                    context_str = chat.get("context_full_text", "")
                    if not context_str:
                        context_str = "\n\n".join(
                            [f"Source: {c['source']}\n{c['text']}" for c in context_data]
                        )
                    download_text = f"Question: {chat['query']}\n\nAnswer: {chat['answer']}\n\nContext:\n{context_str}"

                # Optimized: Use pre-calculated sanitized query for filename from session state.
                sanitized_query = chat.get("sanitized_query_filename")
                if not sanitized_query:
                    sanitized_query = re.sub(
                        r"[^a-z0-9]+", "_", chat["query"][:30].lower()
                    ).strip("_")

                st.download_button(
                    label="Download Answer & Context",
                    data=download_text,
                    file_name=f"bfs_smartbot_answer_{original_idx + 1}_{sanitized_query}.txt",
                    mime="text/plain",
                    key=f"download_{original_idx + 1}",
                    help="Download this specific answer and its supporting context as a text file for your records.",
                    width="stretch",
                    icon=":material/download:",
                )
        st.markdown("---")
