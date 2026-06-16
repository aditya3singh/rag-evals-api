import json
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer

CHUNKS_FILE = Path("data/chunks.json")
OUTPUT_FILE = Path("data/embeddings.npy")
META_FILE = Path("data/embeddings_meta.json")

MODEL_NAME = "all-MiniLM-L6-v2"


def embed_chunks():
    chunks = json.loads(CHUNKS_FILE.read_text(encoding="utf-8"))
    texts = [c["text"] for c in chunks]

    print(f"Loading model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)

    print(f"Embedding {len(texts)} chunks...")
    embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)

    np.save(OUTPUT_FILE, embeddings)

    meta = [{"id": c["id"], "source": c["source"], "chunk_index": c["chunk_index"]} for c in chunks]
    META_FILE.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    print(f"Saved embeddings: {embeddings.shape} -> {OUTPUT_FILE}")
    print(f"Saved metadata -> {META_FILE}")


if __name__ == "__main__":
    embed_chunks()