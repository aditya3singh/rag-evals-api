import json
import re
from pathlib import Path

CORPUS_DIR = Path("data/corpus")
OUTPUT_FILE = Path("data/chunks.json")

MAX_CHUNK_WORDS = 300
MIN_CHUNK_WORDS = 30


def split_by_headers(text: str, source: str):
    sections = re.split(r'\n(?=#{1,3} )', text)
    chunks = []

    for section in sections:
        section = section.strip()
        if not section:
            continue

        words = section.split()

        if len(words) < MIN_CHUNK_WORDS:
            continue

        if len(words) <= MAX_CHUNK_WORDS:
            chunks.append(section)
        else:
            words_list = words
            start = 0
            while start < len(words_list):
                end = start + MAX_CHUNK_WORDS
                chunk_words = words_list[start:end]
                chunk_text = " ".join(chunk_words)
                if len(chunk_words) >= MIN_CHUNK_WORDS:
                    chunks.append(chunk_text)
                start = end

    return chunks


def build_chunks():
    all_chunks = []
    chunk_id = 0

    for path in sorted(CORPUS_DIR.rglob("*.md")):
        content = path.read_text(encoding="utf-8", errors="ignore")
        source = str(path.relative_to(CORPUS_DIR))
        text_chunks = split_by_headers(content, source)

        for i, chunk in enumerate(text_chunks):
            all_chunks.append({
                "id": chunk_id,
                "source": source,
                "chunk_index": i,
                "text": chunk,
            })
            chunk_id += 1

    OUTPUT_FILE.write_text(json.dumps(all_chunks, indent=2), encoding="utf-8")
    print(f"Created {len(all_chunks)} chunks from {len(list(CORPUS_DIR.rglob('*.md')))} files")
    print(f"Saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    build_chunks()
