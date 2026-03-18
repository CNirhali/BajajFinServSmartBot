import bot
import time
import re

text = "This is a sample text with a link [click here](javascript:alert('XSS')) and an image ![alt](http://example.com/img.png). Also some random protocols like data:image/png;base64,abc and file:///etc/passwd."

# Warm up
bot.sanitize_markdown(text)

start = time.perf_counter()
for _ in range(1000):
    bot.sanitize_markdown(text)
end = time.perf_counter()

print(f"Time for 1000 calls: {end - start:.4f}s")
print(f"Average time per call: {(end - start) / 1000:.6f}s")
