from fastapi import FastAPI
from pydantic import BaseModel
from app.retrieval.retriever import retrieve
from app.generation.generator import generate
from app.retrieval.cache import get_cached, set_cached
import time

app = FastAPI(title="RAG Evals API")


class QueryRequest(BaseModel):
    query: str
    top_k: int = 5


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/retrieve")
def retrieve_chunks(request: QueryRequest):
    results = retrieve(request.query, request.top_k)
    return {"query": request.query, "results": results}


@app.post("/ask")
def ask(request: QueryRequest):
    cached = get_cached(request.query, request.top_k)
    if cached:
        cached["cache_hit"] = True
        return cached

    start = time.time()
    chunks = retrieve(request.query, request.top_k)

    if not chunks:
        return {
            "query": request.query,
            "answer": "I could not find relevant information in the documentation.",
            "citations": [],
            "all_sources": [],
            "retrieval_status": "no_results_above_threshold",
            "latency_ms": round((time.time() - start) * 1000),
            "cache_hit": False
        }

    result = generate(request.query, chunks)

    if "NOT_IN_CONTEXT" in result["answer"]:
        return {
            "query": request.query,
            "answer": "I could not find this in the documentation.",
            "citations": [],
            "all_sources": [],
            "retrieval_status": "not_in_context",
            "latency_ms": round((time.time() - start) * 1000),
            "cache_hit": False
        }

    response = {
        "query": request.query,
        "answer": result["answer"],
        "citations": result["citations"],
        "all_sources": result["all_sources"],
        "retrieval_status": "ok",
        "latency_ms": round((time.time() - start) * 1000),
        "cache_hit": False
    }

    set_cached(request.query, request.top_k, response)
    return response
