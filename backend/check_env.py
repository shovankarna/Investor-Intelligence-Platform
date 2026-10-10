"""Comprehensive diagnostic script testing every service and credential in .env."""

import asyncio
import os
import sys

# Ensure UTF-8 output on Windows terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app.core.config import settings

print("========================================")
print("   SYSTEM DIAGNOSTICS & CONNECTIVITY    ")
print("========================================")

# 1. LANGFUSE CHECK
print("\n[1/5] Testing Langfuse Cloud...")
try:
    from langfuse import Langfuse
    lf = Langfuse()
    if lf.auth_check():
        print("  --> Langfuse: SUCCESS (Authenticated with cloud)")
    else:
        print("  --> Langfuse: FAILED (Auth check failed)")
except Exception as e:
    print(f"  --> Langfuse: ERROR ({type(e).__name__}: {e})")

# 2. OPENROUTER API CHECK
print("\n[2/5] Testing OpenRouter API...")
async def test_openrouter():
    try:
        from app.llm.client import llm_client
        res = await llm_client.generate(
            messages=[{"role": "user", "content": "Respond with only: PONG"}],
            max_tokens=10,
            temperature=0.0
        )
        safe_response = res.raw_text.strip().encode("ascii", errors="replace").decode("ascii")
        print(f"  --> OpenRouter: SUCCESS (Model: {res.model_used}, Response: '{safe_response}', Tokens: {res.total_tokens})")
    except Exception as e:
        print(f"  --> OpenRouter: ERROR ({type(e).__name__}: {e})")

asyncio.run(test_openrouter())

# 3. DATABASE & PGVECTOR CHECK
print("\n[3/5] Testing PostgreSQL & pgvector...")
async def test_db():
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text
    try:
        engine = create_async_engine(settings.DATABASE_URL, connect_args={"statement_cache_size": 0})
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            print("  --> Database Connection: SUCCESS")
            
            # Check vector extension
            vec_check = await conn.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'"))
            row = vec_check.fetchone()
            if row:
                print("  --> pgvector Extension: ACTIVE")
            else:
                print("  --> pgvector Extension: NOT DETECTED (attempting to enable...)")
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                print("  --> pgvector Extension: ENABLED")

            # Check tables
            tbl_check = await conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))
            tables = [r[0] for r in tbl_check.fetchall()]
            print(f"  --> Existing Public Tables: {tables if tables else 'None (Migrations not run yet)'}")
            
        await engine.dispose()
    except Exception as e:
        err_msg = str(e)
        if "getaddrinfo failed" in err_msg:
            print(f"  --> Database: HOST NOT FOUND (Check your hostname in DATABASE_URL in .env)")
        else:
            print(f"  --> Database: ERROR ({type(e).__name__}: {e})")

asyncio.run(test_db())

# 4. SUPABASE STORAGE & API CHECK
print("\n[4/5] Testing Supabase Storage & REST API...")
async def test_supabase():
    import httpx
    if not settings.SUPABASE_URL or "your-project" in settings.SUPABASE_URL:
        print("  --> Supabase URL: NOT CONFIGURED")
        return
    try:
        headers = {}
        key = settings.effective_supabase_publishable_key or settings.effective_supabase_secret_key
        if key:
            headers["apikey"] = key
            headers["Authorization"] = f"Bearer {key}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{settings.SUPABASE_URL}/storage/v1/bucket", headers=headers)
            if resp.status_code == 200:
                buckets = [b.get("name") for b in resp.json()] if isinstance(resp.json(), list) else []
                print(f"  --> Supabase Storage API: SUCCESS (Buckets: {buckets})")
            elif resp.status_code in (401, 403):
                print(f"  --> Supabase Storage API: REACHABLE (HTTP {resp.status_code})")
            else:
                print(f"  --> Supabase Storage API: HTTP {resp.status_code}")
    except Exception as e:
        print(f"  --> Supabase API: ERROR ({type(e).__name__}: {e})")

asyncio.run(test_supabase())

# 5. IN-PROCESS ML MODELS CHECK
print("\n[5/5] Testing In-Process Embedding & Reranker Models...")
try:
    from app.rag.embedder import EmbeddingService
    vecs = EmbeddingService.embed_texts(["Test embedding generation"])
    print(f"  --> Embedder (bge-small-en-v1.5): SUCCESS (Dimension: {len(vecs[0])})")
    
    from app.rag.retriever import HybridRetriever
    reranker = HybridRetriever.get_reranker()
    scores = reranker.predict([("What was Apple's revenue?", "Apple revenue was $383 billion in fiscal 2023.")])
    print(f"  --> Reranker (bge-reranker-base): SUCCESS (Sample Relevance Score: {scores[0]:.4f})")
except Exception as e:
    print(f"  --> ML Models: ERROR ({type(e).__name__}: {e})")

print("\n========================================")
print("         DIAGNOSTICS COMPLETE           ")
print("========================================")
