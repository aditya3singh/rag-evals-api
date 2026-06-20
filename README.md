# RAG Evals API

A production-style RAG (Retrieval-Augmented Generation) API built over FastAPI documentation, with a built-in eval harness to measure retrieval accuracy — not just "does it work," but "how well, and how do I know."

![Demo](docs/demo-screenshot.png)

## What this demonstrates

- **RAG fundamentals**: chunking, embeddings, vector similarity search
- **Evaluation-driven development**: a 35-question eval harness used to measure retrieval and answer accuracy across multiple pipeline iterations
- **Production concerns**: caching, hallucination guards, citation tracking, Docker deployment, load testing
- **Cost-conscious engineering**: fully local stack (embeddings + LLM), zero API cost
- **Honest tradeoff analysis**: speed vs. accuracy across model sizes, measured not assumed

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
Ollama qwen2.5:1.5b (local LLM) ── generates answer + citations
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
| LLM | Ollama + qwen2.5:1.5b | Local, free, balances speed and accuracy |
| Caching | TTLCache | Sub-millisecond repeat queries |
| Infra | Docker Compose | One-command reproducibility |
| Load testing | Locust | Measured concurrency behavior, not assumed |

## Eval results

Corpus: 100 FastAPI doc files → 822 chunks. Eval set: 35 questions.

| Stage | Retrieval | Keywords |
|-------|-----------|----------|
| Baseline (word chunking, 56 docs) | 53.3% | 40.0% |
| Header-based chunking | 66.7% | 33.3% |
| Prompt tuning | 73.3% | 20.0% |
| Flexible keyword matching | 73.3% | 60.0% |
| Expanded corpus (100 docs) + smaller model | 51.4% | 65.7% |

Each change was measured before moving to the next. The final row reflects a deliberate tradeoff: a larger, more diverse corpus with a smaller/faster model (1.5B params, ~5-8s/query) instead of a larger one (3.8B params, ~30s/query). Retrieval dropped because the corpus got harder; keyword accuracy rose because the smaller model performs well when given the right context.

## Load testing

Tested with Locust at 10 concurrent users:

| Model | Median /ask latency | Notes |
|-------|---------------------|-------|
| phi3 (3.8B) | ~30,000ms | Requests queue heavily under load |
| qwen2.5:1.5b (1.5B) | ~5,000-8,000ms | Better concurrency, some quality tradeoff |

**Known constraint**: this setup (single Ollama instance, CPU-only, one Mac) cannot reliably serve 20-30 concurrent users with both speed and accuracy. That would require either a hosted LLM API or GPU-backed infrastructure with proper request queuing — out of scope for this project, but understanding *why* is the point.

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
ollama pull qwen2.5:1.5b
```

Visit `http://localhost:8000` for the UI, or `http://localhost:8000/docs` for the API docs.

## API endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check (verifies Ollama connectivity) |
| `/` | GET | Frontend UI |
| `/retrieve` | POST | Retrieve top-k chunks |
| `/ask` | POST | Full RAG answer with citations |

## Run evals

```bash
python -m app.evals.eval_harness
```

## Run load tests

```bash
python -m locust -f app/loadtest/locustfile.py --host http://localhost:8000 --headless -u 10 -r 2 --run-time 2m
```

## Known limitations

- Retrieval accuracy (51.4% on the expanded corpus) has clear room to improve — a cross-encoder reranker is the next logical step
- pgvector index (`ivfflat`, lists=10) is tuned for ~800 chunks; scaling to millions of vectors would need different list counts, possibly a dedicated vector DB (Qdrant, Weaviate)
- The embedding model (MiniLM-L6, 384-dim) is small; larger embedding models would likely improve retrieval at the cost of speed/storage
- No authentication or rate limiting on the API
- Cannot currently serve 20-30 concurrent users with both speed and accuracy on local hardware — a real infrastructure constraint, not a code bug

## What I learned

- Corpus curation matters more than model choice — one 52K-word changelog file would have dominated the embeddings
- Header-based chunking outperforms naive word-count splitting for structured docs
- Evals reveal problems invisible to manual testing — and bigger eval sets reveal *different* problems than small ones
- Speed and accuracy are a real tradeoff in local LLM serving — there's no free lunch without paid APIs or GPU infrastructure
- Docker networking: a container's `localhost` is not the host's `localhost` — use `host.docker.internal`
- Health checks should verify real dependencies (Ollama, DB), not just "is the process alive"
