from fastapi import FastAPI, HTTPException, Cookie, Response, Depends, Header
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from app.retrieval.retriever import retrieve
from app.generation.generator import generate
from app.retrieval.cache import get_cached, set_cached
from app.auth.auth import create_user, login_user, get_current_user, logout_user
from app.storage.db_schema import create_tables
import psycopg2
import os
import time
import json
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

app = FastAPI(title="RAG Evals API")

# ── CORS ─────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Startup: ensure DB tables exist ──────────────────────
@app.on_event("startup")
def on_startup():
    try:
        create_tables()
    except Exception as e:
        print(f"Warning: could not create tables on startup: {e}")


# ── Models ──────────────────────────────────────────────
class QueryRequest(BaseModel):
    query: str
    top_k: int = 5
    conversation_id: Optional[int] = None


class AuthRequest(BaseModel):
    email: str
    password: str


# ── Helper ───────────────────────────────────────────────
def get_db():
    return psycopg2.connect(DATABASE_URL)


def get_session_id(session_id: Optional[str] = Cookie(None), authorization: Optional[str] = Header(None)) -> Optional[str]:
    if session_id:
        return session_id
    if authorization and authorization.startswith("Bearer "):
        return authorization.split(" ")[1]
    return None


def require_user(session_id: Optional[str] = Depends(get_session_id)):
    """Return the current user or raise 401."""
    if not session_id:
        raise HTTPException(status_code=401, detail="Not logged in")
    user = get_current_user(session_id)
    if not user:
        raise HTTPException(status_code=401, detail="Session expired")
    return user


# ── Health ──────────────────────────────────────────────
@app.get("/health")
def health():
    try:
        conn = get_db()
        conn.close()
        return {"status": "ok", "db": "connected"}
    except Exception as e:
        return JSONResponse(status_code=503, content={"status": "degraded", "error": str(e)})


# ── Frontend ─────────────────────────────────────────────
@app.get("/")
def serve_frontend():
    return FileResponse("app/static/index.html")


# ── Auth endpoints ────────────────────────────────────────
@app.post("/auth/signup")
def signup(req: AuthRequest, response: Response):
    try:
        user = create_user(req.email, req.password)
        return {"message": "User created", "user": user}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/auth/login")
def login(req: AuthRequest, response: Response):
    try:
        result = login_user(req.email, req.password)
        response.set_cookie(
            key="session_id",
            value=result["session_id"],
            httponly=True,
            max_age=86400,
            samesite="none",
            secure=True
        )
        return {"message": "Login successful", "email": result["email"], "session_id": result["session_id"]}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@app.post("/auth/logout")
def logout(response: Response, session_id: Optional[str] = Depends(get_session_id)):
    if session_id:
        logout_user(session_id)
    response.delete_cookie("session_id")
    return {"message": "Logged out"}


@app.get("/auth/me")
def me(session_id: Optional[str] = Depends(get_session_id)):
    if not session_id:
        raise HTTPException(status_code=401, detail="Not logged in")
    user = get_current_user(session_id)
    if not user:
        raise HTTPException(status_code=401, detail="Session expired")
    return user


# ── Conversation endpoints ────────────────────────────────
@app.post("/conversations")
def create_conversation(user: dict = Depends(require_user)):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO conversations (user_id, title) VALUES (%s, %s) RETURNING id, title, created_at",
            (user["id"], "New conversation")
        )
        conv = cur.fetchone()
        conn.commit()
        cur.close()
    finally:
        conn.close()
    return {"id": conv[0], "title": conv[1], "created_at": str(conv[2])}


@app.get("/conversations")
def list_conversations(user: dict = Depends(require_user)):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, title, created_at, updated_at FROM conversations WHERE user_id = %s ORDER BY updated_at DESC",
            (user["id"],)
        )
        rows = cur.fetchall()
        cur.close()
    finally:
        conn.close()
    return [{"id": r[0], "title": r[1], "created_at": str(r[2]), "updated_at": str(r[3])} for r in rows]


@app.get("/conversations/{conversation_id}/messages")
def get_messages(conversation_id: int, user: dict = Depends(require_user)):
    conn = get_db()
    try:
        cur = conn.cursor()
        # Verify the conversation belongs to this user
        cur.execute(
            "SELECT id FROM conversations WHERE id = %s AND user_id = %s",
            (conversation_id, user["id"])
        )
        if not cur.fetchone():
            raise HTTPException(status_code=403, detail="Access denied")
        cur.execute(
            "SELECT id, role, content, citations, created_at FROM messages WHERE conversation_id = %s ORDER BY created_at ASC",
            (conversation_id,)
        )
        rows = cur.fetchall()
        cur.close()
    finally:
        conn.close()
    return [{"id": r[0], "role": r[1], "content": r[2], "citations": r[3], "created_at": str(r[4])} for r in rows]


# ── RAG endpoints ─────────────────────────────────────────
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
            "citations": [], "all_sources": [],
            "retrieval_status": "no_results_above_threshold",
            "latency_ms": round((time.time() - start) * 1000),
            "cache_hit": False
        }

    result = generate(request.query, chunks)

    if "NOT_IN_CONTEXT" in result["answer"]:
        return {
            "query": request.query,
            "answer": "I could not find this in the documentation.",
            "citations": [], "all_sources": [],
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

    # Save to conversation history if conversation_id provided
    if request.conversation_id:
        try:
            conn = get_db()
            try:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO messages (conversation_id, role, content, citations) VALUES (%s, %s, %s, %s)",
                    (request.conversation_id, "user", request.query, None)
                )
                cur.execute(
                    "INSERT INTO messages (conversation_id, role, content, citations) VALUES (%s, %s, %s, %s)",
                    (request.conversation_id, "assistant", result["answer"], json.dumps(result["citations"]))
                )
                cur.execute(
                    "UPDATE conversations SET updated_at = NOW(), title = %s WHERE id = %s AND title = 'New conversation'",
                    (request.query[:50], request.conversation_id)
                )
                conn.commit()
                cur.close()
            finally:
                conn.close()
        except Exception as e:
            print(f"Failed to save message: {e}")

    set_cached(request.query, request.top_k, response)
    return response


# ── Export endpoint ───────────────────────────────────────
@app.get("/conversations/{conversation_id}/export")
def export_conversation(conversation_id: int, user: dict = Depends(require_user)):
    conn = get_db()
    try:
        cur = conn.cursor()
        # Verify the conversation belongs to this user
        cur.execute(
            "SELECT id FROM conversations WHERE id = %s AND user_id = %s",
            (conversation_id, user["id"])
        )
        if not cur.fetchone():
            raise HTTPException(status_code=403, detail="Access denied")
        cur.execute(
            "SELECT role, content, citations, created_at FROM messages WHERE conversation_id = %s ORDER BY created_at ASC",
            (conversation_id,)
        )
        rows = cur.fetchall()
        cur.close()
    finally:
        conn.close()

    text = f"Conversation #{conversation_id}\n{'='*40}\n\n"
    for row in rows:
        role = "You" if row[0] == "user" else "Assistant"
        text += f"{role}:\n{row[1]}\n"
        if row[2]:
            citations = row[2] if isinstance(row[2], list) else json.loads(row[2])
            if citations:
                text += "Sources: " + ", ".join(c.get("source", "") for c in citations) + "\n"
        text += f"\n"

    return Response(
        content=text,
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename=conversation_{conversation_id}.txt"}
    )
