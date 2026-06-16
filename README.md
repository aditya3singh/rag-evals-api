# RAG Evals API

A production-style RAG (Retrieval-Augmented Generation) API built over FastAPI documentation, with a built-in eval harness to measure retrieval accuracy.

## What makes this different

Most RAG projects stop at "it works on my test question." This one includes:
- A 15-question eval set with expected sources and keywords
- An eval harness that produces retrieval and keyword accuracy scores
- Iterative improvement tracked via eval scores (not guesswork)

## Tech stack

- **Backend:** FastAPI, Pydantic
- **Embeddings:** sentence-transformers (local, free, no API cost)
- **Vector store:** PostgreSQL + pgvector
- **LLM:** Ollama + phi3 (local, free, self-hosted)
- **Caching:** TTLCache (1hr expiry)
- **Infra:** Docker Compose

## Architecture
## Eval results (current)

| Metric | Score |
|--------|-------|
| Retrieval accuracy | 73.3% (11/15) |
| Keyword accuracy | 60.0% (9/15) |

## Quick start

```bash
# 1. Clone and setup
git clone <your-repo-url>
cd rag-evals-api

# 2. Add FastAPI docs corpus
cd data && git clone --depth 1 https://github.com/tiangolo/fastapi.git temp
mkdir -p docs && cp -r temp/docs/en/docs/* docs/ && rm -rf temp && cd ..

# 3. Run ingestion pipeline
python -m app.ingestion.filter_corpus
python -m app.ingestion.chunker
python -m app.ingestion.embed_chunks

# 4. Start stack
docker-compose up -d

# 5. Load embeddings to DB
python -m app.ingestion.load_to_db

# 6. Start Ollama separately
ollama serve
ollama pull phi3
```

## API endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/retrieve` | POST | Retrieve top-k chunks |
| `/ask` | POST | Full RAG answer with citations |

## Run evals

```bash
python -m app.evals.eval_harness
```

## What I learned

- Corpus curation matters more than model choice
- Header-based chunking improved retrieval from 53% to 67%
- Similarity threshold tuning: 0.55 was too strict, 0.45 works better
- Local embeddings (sentence-transformers) are viable for portfolio projects
- Evals reveal problems that manual testing misses every time
