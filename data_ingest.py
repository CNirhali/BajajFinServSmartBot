import os
import glob
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
        df = pd.read_csv(csv_path)
        # For simplicity, treat each row as a chunk
        for idx, row in df.iterrows():
            chunk = row.to_json()
            csv_chunks.append({
                'source': os.path.basename(csv_path),
                'text': chunk
            })
    return csv_chunks

# 3. Embed and store in ChromaDB
def embed_and_store(chunks):
    model = SentenceTransformer('all-MiniLM-L6-v2')
    chroma_client = chromadb.Client(Settings(persist_directory=CHROMA_DB_DIR))
    collection = chroma_client.get_or_create_collection('bfs_smartbot')
    texts = [c['text'] for c in chunks]
    metadatas = [{'source': c['source']} for c in chunks]
    embeddings = model.encode(texts).tolist()
    ids = [f"doc_{i}" for i in range(len(texts))]
    collection.add(documents=texts, embeddings=embeddings, metadatas=metadatas, ids=ids)
    chroma_client.persist()

if __name__ == '__main__':
    pdf_chunks = parse_pdfs()
    csv_chunks = parse_csvs()
    all_chunks = pdf_chunks + csv_chunks
    embed_and_store(all_chunks)
    print(f"Ingested and indexed {len(all_chunks)} chunks.") 