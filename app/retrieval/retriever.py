import numpy as np
import psycopg2
import os
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
MODEL_NAME = "all-MiniLM-L6-v2"
SIMILARITY_THRESHOLD = 0.45

model = SentenceTransformer(MODEL_NAME)


def retrieve(query: str, top_k: int = 5):
    query_embedding = model.encode([query], convert_to_numpy=True)[0]

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, source, chunk_index, text,
               1 - (embedding <=> %s::vector) AS similarity
        FROM chunks
        WHERE 1 - (embedding <=> %s::vector) >= %s
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    """, (
        query_embedding.tolist(),
        query_embedding.tolist(),
        SIMILARITY_THRESHOLD,
        query_embedding.tolist(),
        top_k
    ))

    rows = cur.fetchall()
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
