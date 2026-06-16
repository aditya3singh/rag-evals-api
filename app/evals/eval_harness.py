import json
import requests
from pathlib import Path
from datetime import datetime

EVAL_FILE = Path("app/evals/eval_questions.json")
API_URL = "http://localhost:8000/ask"
RESULTS_FILE = Path("app/evals/eval_results.json")
KEYWORD_THRESHOLD = 0.6


def run_evals():
    questions = json.loads(EVAL_FILE.read_text())
    results = []
    retrieval_correct = 0
    keyword_correct = 0
    total = len(questions)

    print(f"Running {total} eval questions...\n")

    for q in questions:
        print(f"Q{q['id']}: {q['question'][:60]}...")

        response = requests.post(API_URL, json={
            "query": q["question"],
            "top_k": 5
        })
        data = response.json()

        answer = data.get("answer", "").lower()
        all_sources = data.get("all_sources", [])
        retrieval_status = data.get("retrieval_status", "")

        source_hit = any(
            expected in all_sources
            for expected in q["expected_sources"]
        )

        keyword_score = sum(
            kw.lower() in answer
            for kw in q["expected_answer_keywords"]
        ) / len(q["expected_answer_keywords"])
        keyword_hit = keyword_score >= KEYWORD_THRESHOLD

        if source_hit:
            retrieval_correct += 1
        if keyword_hit:
            keyword_correct += 1

        result = {
            "id": q["id"],
            "question": q["question"],
            "expected_sources": q["expected_sources"],
            "retrieved_sources": all_sources,
            "source_hit": source_hit,
            "expected_keywords": q["expected_answer_keywords"],
            "keyword_score": round(keyword_score, 2),
            "keyword_hit": keyword_hit,
            "retrieval_status": retrieval_status,
            "answer_preview": data.get("answer", "")[:200]
        }
        results.append(result)

        status = "✓" if source_hit and keyword_hit else "✗"
        print(f"  {status} source: {source_hit} | keywords: {keyword_hit} ({round(keyword_score*100)}%) | status: {retrieval_status}\n")

    retrieval_score = round(retrieval_correct / total * 100, 1)
    keyword_score_pct = round(keyword_correct / total * 100, 1)

    summary = {
        "timestamp": datetime.now().isoformat(),
        "total": total,
        "retrieval_correct": retrieval_correct,
        "keyword_correct": keyword_correct,
        "retrieval_score": f"{retrieval_score}%",
        "keyword_score": f"{keyword_score_pct}%",
        "results": results
    }

    RESULTS_FILE.write_text(json.dumps(summary, indent=2))

    print("=" * 50)
    print(f"Retrieval score:  {retrieval_correct}/{total} ({retrieval_score}%)")
    print(f"Keyword score:    {keyword_correct}/{total} ({keyword_score_pct}%)")
    print(f"Results saved to: {RESULTS_FILE}")


if __name__ == "__main__":
    run_evals()
