# Deployment Guide

This guide covers deploying the RAG Evals API to production for public use.

## ⚠️ Important Security Considerations

Before deploying publicly, you **must** address these security concerns:

1. **Authentication** - Currently no auth is implemented
2. **Rate Limiting** - No protection against abuse
3. **API Keys** - Secure your environment variables
4. **CORS** - Configure allowed origins properly
5. **HTTPS** - Use SSL/TLS certificates

## Deployment Options

### Option 1: Railway (Recommended - Easiest)

Railway provides free tier and easy deployment with PostgreSQL included.

1. **Prepare your repository**
   ```bash
   # Make sure .gitignore is correct
   git add .
   git commit -m "Prepare for deployment"
   git push origin main
   ```

2. **Deploy to Railway**
   - Go to [railway.app](https://railway.app)
   - Click "Start a New Project"
   - Select "Deploy from GitHub repo"
   - Choose your `rag-evals-api` repository
   - Railway will auto-detect the Dockerfile

3. **Add PostgreSQL**
   - In Railway dashboard, click "New" → "Database" → "PostgreSQL"
   - Railway will automatically set `DATABASE_URL` environment variable

4. **Set Environment Variables**
   In Railway project settings, add:
   ```
   DATABASE_URL=<auto-set-by-railway>
   OLLAMA_BASE_URL=<your-ollama-instance-url>
   POSTGRES_DB=rag_evals
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=<generate-secure-password>
   ```

5. **Ollama Hosting**
   - Railway doesn't support Ollama directly (requires GPU)
   - Options:
     a. Use [Replicate](https://replicate.com) API instead
     b. Host Ollama on [Modal](https://modal.com) or [RunPod](https://runpod.io)
     c. Switch to OpenAI API (paid but simple)

6. **Generate Domain**
   - Railway provides a free `.railway.app` domain
   - Or add your custom domain in settings

### Option 2: Render

Similar to Railway but with more free tier limitations.

1. Go to [render.com](https://render.com)
2. Create new Web Service from GitHub repo
3. Add PostgreSQL database
4. Set environment variables
5. Deploy

### Option 3: Fly.io

Good for Docker-based deployments with global distribution.

```bash
# Install flyctl
brew install flyctl

# Login
flyctl auth login

# Launch app
flyctl launch

# Add PostgreSQL
flyctl postgres create

# Deploy
flyctl deploy
```

### Option 4: AWS/GCP/Azure (Most Scalable)

For production-grade deployment:

1. **AWS ECS + RDS**
   - Push Docker image to ECR
   - Deploy to ECS Fargate
   - Use RDS for PostgreSQL
   - Use API Gateway for rate limiting
   - Use Secrets Manager for credentials

2. **Google Cloud Run + Cloud SQL**
   - Deploy container to Cloud Run
   - Use Cloud SQL for PostgreSQL
   - Use Secret Manager
   - Add Cloud Load Balancer

## Switching to OpenAI API (Easiest for Public Deployment)

Since hosting Ollama publicly is complex, consider switching to OpenAI:

1. **Update `app/generation/generator.py`**
   ```python
   from openai import OpenAI
   
   client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
   
   response = client.chat.completions.create(
       model="gpt-3.5-turbo",
       messages=[{"role": "user", "content": prompt}],
       temperature=0.7
   )
   ```

2. **Add to environment variables**
   ```
   OPENAI_API_KEY=sk-...
   ```

3. **Update requirements.txt**
   ```
   openai>=1.0.0
   ```

## Post-Deployment Checklist

- [ ] Health check endpoint works: `/health`
- [ ] Database connection successful
- [ ] LLM endpoint accessible
- [ ] Test `/retrieve` endpoint
- [ ] Test `/ask` endpoint
- [ ] Monitor logs for errors
- [ ] Set up monitoring (Sentry, LogDNA, etc.)
- [ ] Configure backups for PostgreSQL
- [ ] Add rate limiting (nginx, Cloudflare, or app-level)
- [ ] Add authentication if needed
- [ ] Update CORS settings for your domain
- [ ] Test with real queries
- [ ] Monitor costs (if using paid APIs)

## Adding Authentication (Optional)

For basic API key authentication:

1. **Update `app/auth/auth.py`**
   ```python
   from fastapi import Header, HTTPException
   import os
   
   async def verify_api_key(x_api_key: str = Header(...)):
       valid_key = os.getenv("API_KEY")
       if x_api_key != valid_key:
           raise HTTPException(status_code=403, detail="Invalid API key")
       return x_api_key
   ```

2. **Protect endpoints in `app/main.py`**
   ```python
   from app.auth.auth import verify_api_key
   from fastapi import Depends
   
   @app.post("/ask", dependencies=[Depends(verify_api_key)])
   async def ask_endpoint(request: AskRequest):
       ...
   ```

3. **Set API_KEY environment variable**

## Adding Rate Limiting

Use `slowapi` for request limiting:

```bash
pip install slowapi
```

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/ask")
@limiter.limit("10/minute")
async def ask_endpoint(request: Request):
    ...
```

## Monitoring

Add basic monitoring:

```python
import sentry_sdk

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    traces_sample_rate=0.1
)
```

## Cost Estimation

**If using OpenAI API (gpt-3.5-turbo):**
- ~$0.0015 per request (average)
- 1,000 requests = ~$1.50
- 100,000 requests = ~$150

**If using hosted infrastructure:**
- Railway: $5-20/month (small app)
- Render: $7-25/month
- AWS: $20-100/month (depending on traffic)

## Support

For issues during deployment:
- Check logs: `docker logs <container_id>`
- Test locally first: `docker-compose up`
- Verify environment variables are set
- Check database connectivity: `/health` endpoint
