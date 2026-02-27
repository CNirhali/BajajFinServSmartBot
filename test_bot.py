from bot import answer_query

TEST_QUERIES = [
    "Summarize the key points from the Q1 FY25 earnings call.",
    "What was the closing price of BFS on 2024-01-02?",
    "Compare the closing prices of BFS and Sensex on 2024-01-02.",
    "What guidance did management give for FY25?",
    "List any risks or challenges mentioned in the Q4 FY25 earnings call.",
    "How did BFS perform compared to Sensex in January 2024?",
    "What were the main questions from analysts in the Q2 FY25 call?",
]

import requests

def run_tests():
    for q in TEST_QUERIES:
        print(f"\n=== Query: {q}")
        try:
            answer, context = answer_query(q)
            print(f"Answer: {answer}\n---\nContext:\n{context}\n")
        except requests.exceptions.ConnectionError:
            print("Warning: Could not connect to Ollama server. Skipping query execution.")
            # We only skip this one; if CI should pass even if Ollama is down, this is fine.

if __name__ == '__main__':
    run_tests() 