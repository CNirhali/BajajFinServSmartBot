import time
import re

# Simulated context string as it currently exists
def get_mock_context(num_sources=5, chunks_per_source=2):
    lines = []
    for i in range(num_sources):
        source = f"Document_{i}.pdf"
        for j in range(chunks_per_source):
            lines.append(f"Source: {source}")
            lines.append(f"This is some sample text for chunk {j} of source {i}. " * 10)
    return "\n".join(lines)

# Current parsing logic from app.py
def current_parsing_logic(context_str):
    # 1. Extract unique sources for label
    sources = sorted(
        list(
            set(
                line.replace("Source:", "").strip()
                for line in context_str.split("\n")
                if line.startswith("Source:")
            )
        )
    )
    source_names = ", ".join(sources)
    if len(source_names) > 60:
        source_names = source_names[:57] + "..."

    expander_label = f"🔍 Show context from {len(sources)} sources"
    if sources:
        expander_label += f": {source_names}"

    # 2. Group by source for rendering
    context_lines = context_str.split("\n")
    current_source = None
    current_content = []
    blocks = []

    for line in context_lines:
        if line.startswith("Source:"):
            if current_source and current_content:
                blocks.append((current_source, "\n".join(current_content)))
                current_content = []
            current_source = line
        else:
            if line.strip():
                current_content.append(line)
    if current_source and current_content:
        blocks.append((current_source, "\n".join(current_content)))

    return expander_label, blocks

# Proposed structured logic
def proposed_structured_logic(context_list):
    # context_list is list of dicts: [{'source': '...', 'text': '...'}]

    # 1. Extract unique sources for label
    sources = sorted(list(set(c['source'] for c in context_list)))
    source_names = ", ".join(sources)
    if len(source_names) > 60:
        source_names = source_names[:57] + "..."

    expander_label = f"🔍 Show context from {len(sources)} sources"
    if sources:
        expander_label += f": {source_names}"

    # 2. Grouping is already mostly done or easier
    from collections import defaultdict
    grouped = defaultdict(list)
    for c in context_list:
        grouped[c['source']].append(c['text'])

    blocks = [(f"Source: {s}", "\n".join(t)) for s, t in grouped.items()]
    return expander_label, blocks

if __name__ == "__main__":
    num_messages = 50
    num_sources = 5
    chunks_per_source = 3

    context_str = get_mock_context(num_sources, chunks_per_source)
    context_list = []
    lines = context_str.split("\n")
    cur_src = None
    for line in lines:
        if line.startswith("Source:"):
            cur_src = line.replace("Source: ", "")
        else:
            context_list.append({'source': cur_src, 'text': line})

    print(f"Benchmarking {num_messages} messages with {num_sources} sources each...")

    start = time.perf_counter()
    for _ in range(num_messages):
        _ = current_parsing_logic(context_str)
    end = time.perf_counter()
    print(f"Current approach: {end - start:.6f} seconds")

    start = time.perf_counter()
    for _ in range(num_messages):
        _ = proposed_structured_logic(context_list)
    end = time.perf_counter()
    print(f"Proposed approach: {end - start:.6f} seconds")
