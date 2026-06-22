from locust import HttpUser, task, between
import random

QUESTIONS = [
    "What is dependency injection in FastAPI?",
    "How do you declare request body in FastAPI?",
    "How do you add query parameters in FastAPI?",
    "What is a path parameter in FastAPI?",
    "How do you handle errors in FastAPI?",
    "How do you deploy FastAPI with Docker?",
    "How do you add middleware in FastAPI?",
    "How do you use background tasks in FastAPI?",
]


class RagApiUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def ask_question(self):
        question = random.choice(QUESTIONS)
        self.client.post("/ask", json={"query": question, "top_k": 5})

    @task(2)
    def health_check(self):
        self.client.get("/health")
