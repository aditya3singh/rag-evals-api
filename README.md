# RAG Evals API

A production-style RAG (Retrieval-Augmented Generation) API built over FastAPI documentation, with a built-in eval harness to measure retrieval accuracy — not just "does it work," but "how well, and how do I know."

![Demo](docs/demo-screenshot.png)

## What this demonstrates

- **RAG fundamentals**: chunking, embeddings, vector similarity search
- **Evaluation-driven development**: a 15-question eval harness used to measure and improve retrieval accuracy from 53% → 73%
- **Production concerns**: caching, hallucination guards, citation tracking, Docker deployment
- **Cost-conscious engineering**: fully local stack (embeddings + LLM), zero API cost

## Architecture

```
User query
    │
    ▼
Cache check (TTLCache, 1hr) ──── hit ──► Return cached response
    │ miss
    ▼
Embed query (sentence-transformers, local)
    │
    ▼
pgvector similarity search (cosine, threshold 0.45)
    │
    ▼
Ollama phi3 (local LLM) ── generates answer + citations
    │
    ▼
Response: answer, citations, sources, latency_ms, cache_hit
```

## Tech stack

| Layer | Choice | Why |
|-------|--------|-----|
| Backend | FastAPI | Async, typed, fast to iterate |
| Embeddings | sentence-transformers (local) | Zero API cost, self-hostable |
| Vector store | PostgreSQL + pgvector | Production-grade, SQL-native |
| LLM | Ollama + phi3 | Local, free, no rate limits |
| Caching | TTLCache | Sub-millisecond repeat queries |
| Infra | Docker Compose | One-command reproducibility |

## Eval results

| Iteration | Retrieval | Keywords |
|-----------|-----------|----------|
| Baseline (word chunking) | 53.3% | 40.0% |
| Header-based chunking | 66.7% | 33.3% |
| Prompt tuning | 73.3% | 20.0% |
| Flexible keyword matching | 73.3% | 60.0% |

Each change was measured before moving to the next — no guesswork.

## Quick start

```bash
git clone https://github.com/aditya3singh/rag-evals-api.git
cd rag-evals-api

# Add FastAPI docs corpus
cd data && git clone --depth 1 https://github.com/tiangolo/fastapi.git temp
mkdir -p docs && cp -r temp/docs/en/docs/* docs/ && rm -rf temp && cd ..

# Run ingestion pipeline
python -m app.ingestion.filter_corpus
python -m app.ingestion.chunker
python -m app.ingestion.embed_chunks

# Start the full stack
docker-compose up -d --build

# Load embeddings into the DB
python -m app.ingestion.load_to_db

# Start Ollama (separately, on host)
ollama serve
ollama pull phi3
```

Visit `http://localhost:8000` for the UI, or `http://localhost:8000/docs` for the API docs.

## API endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/` | GET | Frontend UI |
| `/retrieve` | POST | Retrieve top-k chunks |
| `/ask` | POST | Full RAG answer with citations |

## Run evals

```bash
python -m app.evals.eval_harness
```

## Known limitations

- Retrieval accuracy (73%) has room to improve — a cross-encoder reranker would likely help
- Local LLM (phi3) is smaller and less capable than GPT-4-class models; answer quality reflects that tradeoff
- Eval set is small (15 questions) — a production system would need 100+ for reliable signal
- No authentication or rate limiting on the API yet

## What I learned

- Corpus curation matters more than model choice — one 52K-word changelog file would have dominated the embeddings
- Header-based chunking outperforms naive word-count splitting for structured docs
- Evals reveal problems invisible to manual testing — my first "it looks good" answer hid a 53% retrieval accuracy
- Docker networking: a container's `localhost` is not the host's `localhost` — use `host.docker.internal`
