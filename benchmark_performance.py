import time
import bot
import data_ingest
import os
import numpy as np

def benchmark_ingestion():
    print("Benchmarking Ingestion...")
    # Load model once to exclude its loading time from the ingestion measurement if we want to measure just the process
    # Or include it if we want to see the "force refresh" time in app.
    model = bot.get_embedder()

    start_time = time.perf_counter()
    num_chunks = data_ingest.run_ingestion(model=model)
    end_time = time.perf_counter()

    duration = end_time - start_time
    print(f"Ingested {num_chunks} chunks in {duration:.4f} seconds.")
    return duration, num_chunks

def benchmark_retrieval(queries, iterations=3):
    print(f"\nBenchmarking Retrieval ({iterations} iterations per query)...")
    model = bot.get_embedder() # Ensure model is loaded
    collection = bot.get_collection() # Ensure collection is loaded

    results = []
    for query in queries:
        query_times = []
        for i in range(iterations):
            start_time = time.perf_counter()
            context = bot.retrieve_context(query)
            end_time = time.perf_counter()
            query_times.append(end_time - start_time)

        avg_time = sum(query_times) / iterations
        min_time = min(query_times)
        print(f"Query: '{query[:50]}...' | Avg: {avg_time:.4f}s | Min: {min_time:.4f}s")
        results.append({
            'query': query,
            'avg': avg_time,
            'min': min_time,
            'times': query_times
        })
    return results

def benchmark_embedding(iterations=10):
    print(f"\nBenchmarking Embedding ({iterations} iterations)...")
    model = bot.get_embedder()
    text = "This is a sample sentence for benchmarking the embedding model performance."

    times = []
    for _ in range(iterations):
        start_time = time.perf_counter()
        _ = model.encode([text])
        end_time = time.perf_counter()
        times.append(end_time - start_time)

    avg_time = sum(times) / iterations
    print(f"Avg embedding time: {avg_time:.4f}s")
    return avg_time

if __name__ == "__main__":
    queries = [
        "What was the closing price of BFS on Jan 2, 2024?",
        "Summarize the key points from Q1 earnings call",
        "Compare BFS and Sensex closing prices",
        "What guidance did management give for FY25?",
        "What is the impact of interest rates on BFS?"
    ]

    ingest_duration, num_chunks = benchmark_ingestion()
    embed_avg = benchmark_embedding()
    retrieval_results = benchmark_retrieval(queries)

    print("\n" + "="*30)
    print("SUMMARY")
    print(f"Ingestion: {ingest_duration:.4f}s for {num_chunks} chunks")
    print(f"Avg Embedding: {embed_avg:.4f}s")
    total_avg_retrieval = sum(r['avg'] for r in retrieval_results) / len(retrieval_results)
    print(f"Avg Retrieval: {total_avg_retrieval:.4f}s")
    print("="*30)
