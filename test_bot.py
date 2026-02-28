from bot import answer_query
from unittest.mock import patch

TEST_QUERIES = [
    "Summarize the key points from the Q1 FY25 earnings call.",
    "What was the closing price of BFS on 2024-01-02?",
    "Compare the closing prices of BFS and Sensex on 2024-01-02.",
    "What guidance did management give for FY25?",
    "List any risks or challenges mentioned in the Q4 FY25 earnings call.",
    "How did BFS perform compared to Sensex in January 2024?",
    "What were the main questions from analysts in the Q2 FY25 call?",
]

def run_tests():
    # Mock Ollama call to avoid ConnectionError in CI environments
    with patch('bot.ask_mistral_ollama') as mocked_ask:
        mocked_ask.return_value = "This is a mocked response for CI testing."
        for q in TEST_QUERIES:
            print(f"\n=== Query: {q}")
            answer, context = answer_query(q)
            print(f"Answer: {answer}\n---\nContext:\n{context}\n")

if __name__ == '__main__':
    run_tests() 