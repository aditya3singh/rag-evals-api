# 🚀 Quick Deploy Guide (5 Minutes)

The **fastest** way to get your RAG API public.

## Option 1: Render (Recommended - 100% Free Tier Available)

### Step 1: Prepare Repository
```bash
git add .
git commit -m "Ready for deployment"
git push origin main
```

### Step 2: Deploy on Render

1. Go to https://render.com and sign up
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repo: `rag-evals-api`
4. Fill in:
   - **Name**: `rag-evals-api`
   - **Environment**: `Docker`
   - **Region**: Choose closest to you
   - **Branch**: `main`
   - **Instance Type**: Free (for testing) or Starter ($7/mo)

5. Add **PostgreSQL Database**:
   - Click "New +" → "PostgreSQL"
   - Name: `rag-evals-db`
   - Free tier is enough for testing
   - Copy the **Internal Database URL**

6. Add Environment Variables (in Web Service settings):
   ```
   DATABASE_URL=<paste-internal-database-url-here>
   POSTGRES_DB=rag_evals
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=<from-render-db-settings>
   OPENAI_API_KEY=sk-your-openai-key
   ENVIRONMENT=production
   ```

7. Click **"Create Web Service"**

### Step 3: Wait for Build
- First build takes 5-10 minutes
- Watch logs for any errors
- Once deployed, you'll get a URL like: `https://rag-evals-api.onrender.com`

### Step 4: Test It
```bash
curl https://your-app.onrender.com/health
```

## Option 2: Railway (Also Free Tier)

1. Go to https://railway.app
2. Sign in with GitHub
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your repo
5. Add PostgreSQL: Click "New" → "Database" → "Add PostgreSQL"
6. Add environment variables (same as above)
7. Deploy automatically happens
8. Get your URL: `https://your-app.railway.app`

## Important: Switch to OpenAI API

Since Ollama requires GPU and can't run on free tiers, update your code to use OpenAI:

### Update `app/generation/generator.py`:

```python
import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_answer(query: str, context: str) -> str:
    messages = [
        {"role": "system", "content": "You are a helpful assistant..."},
        {"role": "user", "content": f"Context: {context}\n\nQuestion: {query}"}
    ]
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0.7,
        max_tokens=500
    )
    
    return response.choices[0].message.content
```

### Update `requirements.txt`:
```
fastapi
uvicorn[standard]
pydantic
python-dotenv
openai>=1.0.0
psycopg2-binary
sentence-transformers
numpy
pgvector
```

## After Deployment

1. **Test endpoints**:
   ```bash
   # Health check
   curl https://your-app.onrender.com/health
   
   # Test retrieval
   curl -X POST https://your-app.onrender.com/retrieve \
     -H "Content-Type: application/json" \
     -d '{"query": "What is FastAPI?", "top_k": 3}'
   
   # Test RAG answer
   curl -X POST https://your-app.onrender.com/ask \
     -H "Content-Type: application/json" \
     -d '{"question": "How do I use FastAPI?"}'
   ```

2. **Share your API**:
   - API Docs: `https://your-app.onrender.com/docs`
   - Add this URL to your README
   - Share with recruiters!

## Costs

### Free Tier (Testing):
- Render: Free (with limitations: spins down after inactivity)
- Railway: $5 credit/month (usually enough for testing)
- OpenAI: ~$0.002 per request (1,000 requests = $2)

### Paid Tier (Production):
- Render Starter: $7/month + OpenAI usage
- Railway: $5-20/month + OpenAI usage
- Database: Included in both

### Cost for 1,000 requests/month:
- **Total: ~$9-12/month** (hosting + API calls)

## Troubleshooting

**Build fails?**
- Check Dockerfile is valid
- Ensure requirements.txt has all dependencies
- Check logs in platform dashboard

**Database connection error?**
- Verify DATABASE_URL is set correctly
- Use "Internal Database URL" not external
- Check database is in same region

**Health check fails?**
- Check `/health` endpoint in code
- Verify all environment variables are set
- Check logs for Python errors

**OpenAI API error?**
- Verify OPENAI_API_KEY is set correctly
- Check you have credits in OpenAI account
- Try with `gpt-3.5-turbo` first (cheaper)

## Next Steps

After successful deployment:
1. Add rate limiting (see DEPLOYMENT.md)
2. Add authentication if needed
3. Set up monitoring (Sentry, LogDNA)
4. Configure custom domain
5. Add HTTPS certificate (usually automatic)
6. Update README with live demo link

## Live Demo URL

Once deployed, add to your README:

```markdown
## 🌐 Live Demo

**API**: https://your-app.onrender.com
**API Docs**: https://your-app.onrender.com/docs

Try it:
\`\`\`bash
curl -X POST https://your-app.onrender.com/ask \\
  -H "Content-Type: application/json" \\
  -d '{"question": "What is FastAPI?"}'
\`\`\`
```

---

**Questions?** Check the full DEPLOYMENT.md guide for advanced options.
