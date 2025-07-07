# Bajaj Finserv SmartBot

A private, local smart assistant for answering queries about your uploaded Earnings Call Transcripts and financial data (PDF/CSV), powered by Mistral LLM (via Ollama), ChromaDB, and Streamlit.

## Features
- **Local & Private:** Only uses files you upload or place in the project folder. No online search or external data.
- **PDF & CSV Parsing:** Ingests and indexes your financial documents and data.
- **Semantic Search:** Retrieves relevant context using embeddings and ChromaDB.
- **LLM-Powered Answers:** Uses your local Mistral LLM (Ollama) for natural language answers.
- **Modern UI:** Streamlit web app with file upload, analytics, chat history, and download options.
- **Admin Panel:** Re-index files and manage your knowledge base from the UI.
- **Password Protection:** Simple login for access control.
- **Analytics:** Visualizes BFS & Sensex price trends if CSVs are present.

---

## Quickstart

### 1. Install dependencies
```sh
pip install -r requirements.txt
```

### 2. Run the app
```sh
streamlit run app.py
```

- Open [http://localhost:8501](http://localhost:8501) in your browser.
- Login with the password (`bajajgpt2024` by default).

---

## Docker Usage

### 1. Build the Docker image
```sh
docker build -t bajajfinserv-smartbot .
```

### 2. Run the Docker container
```sh
docker run -p 8501:8501 bajajfinserv-smartbot
```
- Open [http://localhost:8501](http://localhost:8501) in your browser.

### 3. (Optional) Persist uploaded files and data
To keep your uploaded files and data between runs, mount the current directory:
```sh
docker run -p 8501:8501 -v $(pwd):/app bajajfinserv-smartbot
```

---

## Notes
- The app only uses files in the project folder or uploaded via the UI. No external data is accessed.
- Requires a local Ollama server running the Mistral model for LLM answers.
- For advanced deployment (cloud, HTTPS, etc.), see Streamlit and Docker documentation.