#!/usr/bin/env python3
"""
migrate_to_supabase.py
----------------------
Migrates the chunks table (with vector embeddings) from your local
PostgreSQL to Supabase.

Usage:
    python migrate_to_supabase.py <SUPABASE_DATABASE_URL>

Example:
    python migrate_to_supabase.py "postgresql://postgres:password@db.xxxx.supabase.co:5432/postgres"
"""

import sys
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

LOCAL_URL = os.getenv("DATABASE_URL", "postgresql://raguser:ragpass@localhost:5433/ragdb")

def migrate(supabase_url: str):
    print("Connecting to local DB...")
    local = psycopg2.connect(LOCAL_URL)
    local_cur = local.cursor()

    print("Connecting to Supabase...")
    remote = psycopg2.connect(supabase_url)
    remote_cur = remote.cursor()

    # ── Setup remote schema ──────────────────────────────────
    print("Setting up Supabase schema...")
    remote_cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    remote_cur.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id SERIAL PRIMARY KEY,
            source TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            text TEXT NOT NULL,
            embedding vector(384)
        );
    """)
    remote_cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)
    remote_cur.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            title TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
    """)
    remote_cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            conversation_id INTEGER REFERENCES conversations(id) ON DELETE CASCADE,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            citations JSONB,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)
    remote.commit()
    print("Schema created.")

    # ── Migrate chunks ───────────────────────────────────────
    print("Fetching chunks from local DB...")
    local_cur.execute("SELECT id, source, chunk_index, text, embedding FROM chunks ORDER BY id")
    rows = local_cur.fetchall()
    print(f"Found {len(rows)} chunks. Migrating...")

    remote_cur.execute("TRUNCATE TABLE chunks RESTART IDENTITY CASCADE;")

    batch_size = 50
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i+batch_size]
        for row in batch:
            remote_cur.execute(
                "INSERT INTO chunks (source, chunk_index, text, embedding) VALUES (%s, %s, %s, %s)",
                (row[1], row[2], row[3], row[4])
            )
        remote.commit()
        print(f"  Migrated {min(i+batch_size, len(rows))}/{len(rows)} chunks...")

    # ── Verify ───────────────────────────────────────────────
    remote_cur.execute("SELECT COUNT(*) FROM chunks")
    count = remote_cur.fetchone()[0]
    print(f"\n✅ Migration complete! {count} chunks in Supabase.")

    local_cur.close()
    local.close()
    remote_cur.close()
    remote.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python migrate_to_supabase.py <SUPABASE_DATABASE_URL>")
        print('Example: python migrate_to_supabase.py "postgresql://postgres:password@db.xxx.supabase.co:5432/postgres"')
        sys.exit(1)
    migrate(sys.argv[1])
