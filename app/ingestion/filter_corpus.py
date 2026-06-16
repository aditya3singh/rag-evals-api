import shutil
from pathlib import Path

SOURCE_DIR = Path("data/docs")
TARGET_DIR = Path("data/corpus")

# Folders/files to include
INCLUDE_DIRS = ["tutorial"]
INCLUDE_FILES = [
    "index.md",
    "async.md",
    "deployment/index.md",
    "deployment/concepts.md",
    "deployment/docker.md",
    "virtual-environments.md",
]

# Minimum word count to keep a file (filters out stub/index pages)
MIN_WORDS = 50


def should_include(path: Path) -> bool:
    rel = path.relative_to(SOURCE_DIR)
    rel_str = str(rel)

    if rel_str in INCLUDE_FILES:
        return True

    if any(rel_str.startswith(d + "/") for d in INCLUDE_DIRS):
        return True

    return False


def filter_corpus():
    if TARGET_DIR.exists():
        shutil.rmtree(TARGET_DIR)
    TARGET_DIR.mkdir(parents=True)

    copied = 0
    skipped_small = 0

    for path in SOURCE_DIR.rglob("*.md"):
        if not should_include(path):
            continue

        content = path.read_text(encoding="utf-8", errors="ignore")
        word_count = len(content.split())

        if word_count < MIN_WORDS:
            skipped_small += 1
            continue

        rel = path.relative_to(SOURCE_DIR)
        dest = TARGET_DIR / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(path, dest)
        copied += 1

    print(f"Copied {copied} files to {TARGET_DIR}")
    print(f"Skipped {skipped_small} files (too small)")


if __name__ == "__main__":
    filter_corpus()