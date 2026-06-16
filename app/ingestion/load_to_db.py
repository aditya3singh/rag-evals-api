import json
import numpy as np
import psycopg2
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

EMBEDDINGS_FILE = Path("data/embeddings.npy")
CHUNKS_FILE = Path("data/chunks.json")


def load_to_db():
    embeddings = np.load(EMBEDDINGS_FILE)
    chunks = json.loads(CHUNKS_FILE.read_text(encoding="utf-8"))

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    # Enable pgvector extension
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # Create table
    cur.execute("""
        DROP TABLE IF EXISTS chunks;
        CREATE TABLE chunks (
            id INTEGER PRIMARY KEY,
            source TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            text TEXT NOT NULL,
            embedding vector(384)
        );
    """)

    # Insert each chunk + embedding
    for chunk, emb in zip(chunks, embeddings):
        cur.execute(
            """
            INSERT INTO chunks (id, source, chunk_index, text, embedding)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (chunk["id"], chunk["source"], chunk["chunk_index"], chunk["text"], emb.tolist())
        )

    # Create an index for faster similarity search
    cur.execute("""
        CREATE INDEX ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10);
    """)

    conn.commit()
    cur.execute("SELECT COUNT(*) FROM chunks;")
    count = cur.fetchone()[0]
    print(f"Loaded {count} chunks into database")

    cur.close()
    conn.close()


if __name__ == "__main__":
    load_to_db()