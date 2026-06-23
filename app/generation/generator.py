from groq import Groq
import os

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = """You are a helpful assistant that answers questions about FastAPI documentation.

Rules:
1. Answer ONLY using the context provided below.
2. If the context contains partial information, use it to give the best possible answer.
3. Only say "NOT_IN_CONTEXT" if the context has absolutely zero relevant information.
4. Always mention keywords from the context in your answer.
5. Be concise — 3-5 sentences maximum.
6. Reference sources as [1], [2], [3] where applicable."""


def generate(query: str, chunks: list) -> dict:
    context = ""
    for i, chunk in enumerate(chunks):
        context += f"\n[{i+1}] Source: {chunk['source']} (chunk {chunk['chunk_index']})\n{chunk['text']}\n"

    prompt = f"""Context:
{context}

Question: {query}

Answer using the context above. Use keywords from the context directly in your answer:"""

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
    )

    answer = response.choices[0].message.content

    citations = []
    for i, chunk in enumerate(chunks):
        ref = f"[{i+1}]"
        if ref in answer:
            citations.append({
                "ref": ref,
                "source": chunk["source"],
                "chunk_index": chunk["chunk_index"],
                "similarity": chunk["similarity"],
                "text_preview": chunk["text"][:150] + "..."
            })

    return {
        "answer": answer,
        "citations": citations,
        "all_sources": list(set(chunk["source"] for chunk in chunks))
    }
