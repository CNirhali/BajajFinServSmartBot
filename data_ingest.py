import os
import glob
import json
import pandas as pd
from PyPDF2 import PdfReader
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

# Constants
DATA_DIR = '.'
PDF_GLOB = os.path.join(DATA_DIR, 'Earnings Call Transcript Q*.pdf')
CSV_FILES = [
    os.path.join(DATA_DIR, 'BFS_Daily_Closing_Price.csv'),
    os.path.join(DATA_DIR, 'Sensex_Daily_Historical_Data.csv'),
]
CHROMA_DB_DIR = './chroma_db'
CHUNK_SIZE = 500  # characters
CHUNK_OVERLAP = 100

# 1. Load and chunk PDFs
def parse_pdfs():
    pdf_chunks = []
    for pdf_path in glob.glob(PDF_GLOB):
        reader = PdfReader(pdf_path)
        text = " ".join(page.extract_text() or '' for page in reader.pages)
        # Chunk text
        for i in range(0, len(text), CHUNK_SIZE - CHUNK_OVERLAP):
            chunk = text[i:i+CHUNK_SIZE]
            pdf_chunks.append({
                'source': os.path.basename(pdf_path),
                'text': chunk
            })
    return pdf_chunks

# 2. Load and chunk CSVs
def parse_csvs():
    csv_chunks = []
    for csv_path in CSV_FILES:
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            source = os.path.basename(csv_path)
            # Optimized: Use to_dict('records') instead of iterrows() for better performance
            records = df.to_dict('records')
            for record in records:
                csv_chunks.append({
                    'source': source,
                    'text': json.dumps(record)
                })
    return csv_chunks

# 3. Embed and store in ChromaDB
def embed_and_store(chunks, model=None):
    # Reuse model if provided to save memory and initialization time (~5-10s)
    if model is None:
        model = SentenceTransformer('all-MiniLM-L6-v2')

    chroma_client = chromadb.Client(Settings(persist_directory=CHROMA_DB_DIR))
    collection = chroma_client.get_or_create_collection('bfs_smartbot')

    texts = [c['text'] for c in chunks]
    metadatas = [{'source': c['source']} for c in chunks]

    # Batch encoding is more efficient than individual calls
    embeddings = model.encode(texts, show_progress_bar=False).tolist()

    ids = [f"doc_{i}" for i in range(len(texts))]
    collection.add(documents=texts, embeddings=embeddings, metadatas=metadatas, ids=ids)

    # Safely handle persist() which is deprecated/no-op in newer chromadb versions
    if hasattr(chroma_client, 'persist'):
        try:
            chroma_client.persist()
        except (AttributeError, NotImplementedError):
            pass

def run_ingestion(model=None):
    """
    Main entry point for ingestion.
    Accepts an optional pre-loaded embedding model to avoid redundant loading.
    """
    pdf_chunks = parse_pdfs()
    csv_chunks = parse_csvs()
    all_chunks = pdf_chunks + csv_chunks
    if all_chunks:
        embed_and_store(all_chunks, model=model)
    return len(all_chunks)

if __name__ == '__main__':
    num_chunks = run_ingestion()
    print(f"Ingested and indexed {num_chunks} chunks.")
