import psycopg2
import os
# pyrefly: ignore [missing-import]
from fastembed import TextEmbedding
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
MODEL_NAME = "BAAI/bge-small-en-v1.5"
SIMILARITY_THRESHOLD = 0.1

model = TextEmbedding(MODEL_NAME)


def retrieve(query: str, top_k: int = 7):
    embeddings = list(model.embed([query]))
    embedding_list = embeddings[0].tolist()

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT id, source, chunk_index, text,
                   1 - (embedding <=> %s::vector) AS similarity
            FROM chunks
            WHERE 1 - (embedding <=> %s::vector) >= %s
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """, (
            embedding_list,
            embedding_list,
            SIMILARITY_THRESHOLD,
            embedding_list,
            top_k
        ))

        rows = cur.fetchall()
    finally:
        cur.close()
        conn.close()

    results = []
    for row in rows:
        results.append({
            "id": row[0],
            "source": row[1],
            "chunk_index": row[2],
            "text": row[3],
            "similarity": round(float(row[4]), 4)
        })

    return results