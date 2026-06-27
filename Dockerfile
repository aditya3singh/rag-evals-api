FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the embedding model during build (avoids slow cold starts)
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5')"

# Copy application code
COPY app/ ./app/

# Create non-root user (HuggingFace Spaces requirement)
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app && \
    cp -r /root/.cache /home/appuser/.cache 2>/dev/null && \
    chown -R appuser:appuser /home/appuser/.cache

USER appuser

EXPOSE 7860

# HuggingFace Spaces requires port 7860
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}
