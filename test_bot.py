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
    # Mock the Ollama API call to avoid connection errors in environments without a local Ollama server (e.g. CI)
    with patch('bot.http_session.post') as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
    # Mock Ollama call to avoid ConnectionError in CI environments
    with patch('bot.ask_mistral_ollama') as mocked_ask:
        mocked_ask.return_value = "This is a mocked response for CI testing."

    # Mock both requests.post and requests.Session.post to cover all bases
    with patch('requests.post') as mock_post, \
         patch('requests.Session.post') as mock_session_post:

        mock_response = mock_post.return_value
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'response': 'This is a mocked response for testing purposes.'
        }

        mock_session_post.return_value = mock_response

        for q in TEST_QUERIES:
            print(f"\n=== Query: {q}")
            answer, context = answer_query(q)
            print(f"Answer: {answer}\n---\nContext:\n{context}\n")

if __name__ == '__main__':
    run_tests()
