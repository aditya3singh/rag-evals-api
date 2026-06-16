from cachetools import TTLCache
import hashlib
import json

cache = TTLCache(maxsize=100, ttl=3600)


def make_key(query: str, top_k: int) -> str:
    raw = json.dumps({"query": query.strip().lower(), "top_k": top_k})
    return hashlib.md5(raw.encode()).hexdigest()


def get_cached(query: str, top_k: int):
    key = make_key(query, top_k)
    return cache.get(key)


def set_cached(query: str, top_k: int, value: dict):
    key = make_key(query, top_k)
    cache[key] = value
