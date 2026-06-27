import os
import uuid
import bcrypt
import psycopg2
from dotenv import load_dotenv
from cachetools import TTLCache

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL")
SESSION_TTL = 60 * 60 * 24

# Try Redis first; fall back to in-memory sessions if unavailable
redis_client = None
if REDIS_URL:
    try:
        import redis
        redis_client = redis.from_url(REDIS_URL)
        redis_client.ping()
        print("Session store: Redis")
    except Exception as e:
        print(f"Redis unavailable ({e}), falling back to in-memory sessions")
        redis_client = None

# In-memory fallback (works on platforms without Redis like HuggingFace Spaces)
if redis_client is None:
    print("Session store: in-memory (TTLCache)")

session_cache = TTLCache(maxsize=1000, ttl=SESSION_TTL)


def _session_set(key: str, value: str):
    if redis_client:
        redis_client.setex(key, SESSION_TTL, value)
    else:
        session_cache[key] = value


def _session_get(key: str):
    if redis_client:
        return redis_client.get(key)
    return session_cache.get(key)


def _session_delete(key: str):
    if redis_client:
        redis_client.delete(key)
    else:
        session_cache.pop(key, None)


def get_db():
    return psycopg2.connect(DATABASE_URL)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_user(email: str, password: str) -> dict:
    conn = get_db()
    cur = conn.cursor()
    try:
        password_hash = hash_password(password)
        cur.execute(
            "INSERT INTO users (email, password_hash) VALUES (%s, %s) RETURNING id, email, created_at",
            (email, password_hash)
        )
        user = cur.fetchone()
        conn.commit()
        return {"id": user[0], "email": user[1], "created_at": str(user[2])}
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        raise ValueError("Email already registered")
    finally:
        cur.close()
        conn.close()


def login_user(email: str, password: str) -> dict:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, email, password_hash FROM users WHERE email = %s", (email,))
    user = cur.fetchone()
    cur.close()
    conn.close()

    if not user or not verify_password(password, user[2]):
        raise ValueError("Invalid email or password")

    session_id = str(uuid.uuid4())
    _session_set(f"session:{session_id}", str(user[0]))

    return {"session_id": session_id, "user_id": user[0], "email": user[1]}


def get_current_user(session_id: str) -> dict | None:
    user_id = _session_get(f"session:{session_id}")
    if not user_id:
        return None

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, email FROM users WHERE id = %s", (int(user_id),))
    user = cur.fetchone()
    cur.close()
    conn.close()

    if not user:
        return None
    return {"id": user[0], "email": user[1]}


def logout_user(session_id: str):
    _session_delete(f"session:{session_id}")
