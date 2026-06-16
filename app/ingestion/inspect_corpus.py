import os
from pathlib import Path

DOCS_DIR = Path("data/docs")

def inspect():
    total_files = 0
    total_words = 0
    file_stats = []

    for root, _, files in os.walk(DOCS_DIR):
        for file in files:
            if file.endswith(".md"):
                path = Path(root) / file
                content = path.read_text(encoding="utf-8", errors="ignore")
                word_count = len(content.split())
                total_files += 1
                total_words += word_count
                file_stats.append((str(path), word_count))

    print(f"Total .md files: {total_files}")
    print(f"Total words: {total_words}")
    print(f"Average words per file: {total_words // total_files if total_files else 0}")
    print("\nTop 10 largest files:")
    for path, wc in sorted(file_stats, key=lambda x: -x[1])[:10]:
        print(f"  {wc:6d} words  -  {path}")

    print("\nTop 10 smallest files:")
    for path, wc in sorted(file_stats, key=lambda x: x[1])[:10]:
        print(f"  {wc:6d} words  -  {path}")

if __name__ == "__main__":
    inspect()