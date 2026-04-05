def get_collection():
    """Returns the ChromaDB collection, initializing the client on first call."""
    global _collection
    if _collection is None:
        import chromadb
        # Optimized: Use PersistentClient for better performance and reliable persistence in ChromaDB 0.4+.
        # It replaces the deprecated chromadb.Client(Settings(persist_directory=...)) pattern.
        chroma_client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
        _collection = chroma_client.get_or_create_collection(COLLECTION_NAME)
    return _collection
