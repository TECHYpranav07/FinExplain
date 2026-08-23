import os
import sys

# Ensure UTF-8 output encoding across Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

os.environ["USE_TF"] = "0"
os.environ["USE_TORCH"] = "1"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUTF8"] = "1"

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging

from app.core.config import settings

from app.api.routes.v1 import documents, queries, hilt, products, feedback, analysis, auth, admin

app = FastAPI(
    title="FinExplain API",
    description="Evidence-first AI for loan decisions",
    version="1.0.0"
)


@app.on_event("startup")
async def startup_warmup():
    """
    Validate configuration and pre-load ML models at startup.
    Moves cold-start latency from the first user request to application boot.
    """
    startup_logger = logging.getLogger("startup")

    # 1. Validate Gemini model configuration
    try:
        from app.external.llm_client import validate_model
        validate_model()
    except Exception as e:
        startup_logger.error(f"⚠️ Gemini model validation failed: {e}")

    # 2. Pre-load SentenceTransformer embedding model
    try:
        from app.external.huggingface_client import get_sentence_transformer
        get_sentence_transformer()
        startup_logger.info("✅ SentenceTransformer embedding model loaded")
    except Exception as e:
        startup_logger.warning(f"⚠️ Embedding model pre-load failed: {e}")

    # 3. Pre-load CrossEncoder reranker model
    try:
        from app.rag.retrieval.reranker import get_reranker
        get_reranker()
        startup_logger.info("✅ CrossEncoder reranker model loaded")
    except Exception as e:
        startup_logger.warning(f"⚠️ Reranker model pre-load failed: {e}")

    # 4. Warm Pinecone index connection
    try:
        from app.external.pinecone_client import get_pinecone_index
        get_pinecone_index()
        startup_logger.info("✅ Pinecone index connection warmed")
    except Exception as e:
        startup_logger.warning(f"⚠️ Pinecone warm-up failed: {e}")

    startup_logger.info("🚀 FinExplain startup warm-up complete")


from app.core.security_middleware import SecurityMiddleware

# Enable Security & DDoS Rate Limiting Middleware
app.add_middleware(SecurityMiddleware)

# Enable CORS with origins loaded strictly from .env
_cors_origins = settings.cors_origins_list
if not _cors_origins:
    # If not defined in .env during local development, allow common localhost origins
    _cors_origins = ["http://localhost:5173", "http://localhost:5174", "http://localhost:3000", "http://localhost:8000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register all route handlers
app.include_router(auth.router, prefix="/api/v1", tags=["Auth"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["Documents"])
app.include_router(queries.router, prefix="/api/v1/queries", tags=["Queries"])
app.include_router(hilt.router, prefix="/api/v1/hilt", tags=["HILT"])
app.include_router(products.router, prefix="/api/v1/products", tags=["Products"])
app.include_router(feedback.router, prefix="/api/v1/feedback", tags=["Feedback"])
app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["Analysis"])
app.include_router(admin.router, prefix="/api/v1", tags=["Admin"])

import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse

frontend_dist = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend", "dist")
frontend_assets = os.path.join(frontend_dist, "assets")

if os.path.exists(frontend_assets):
    app.mount("/assets", StaticFiles(directory=frontend_assets), name="assets")

@app.get("/", response_class=HTMLResponse)
async def root():
    index_path = os.path.join(frontend_dist, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h1>FinExplain API</h1><p>Frontend built bundle not found. Run 'npm run build' or use Vite dev server.</p>")

@app.get("/app/{full_path:path}", response_class=HTMLResponse)
@app.get("/app", response_class=HTMLResponse)
async def serve_app():
    index_path = os.path.join(frontend_dist, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h1>FinExplain Frontend Console</h1><p>Run 'npm run build' in frontend/ to generate dist bundle, or visit <a href='/console'>/console</a>.</p>")

@app.get("/console", response_class=HTMLResponse)
async def serve_console():
    console_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend", "console.html")
    if os.path.exists(console_path):
        return FileResponse(console_path)
    return HTMLResponse("<h1>FinExplain Console</h1><p>frontend/console.html not found.</p>")

logger = logging.getLogger(__name__)

@app.get("/health")
async def health_check():
    """Backward-compatible health endpoint (FIN-033: delegates to readiness)."""
    result = await health_ready()
    return result

@app.get("/health/live")
async def health_live():
    """Liveness probe — always returns ok if the process is running."""
    return {"status": "ok"}

@app.get("/health/ready")
async def health_ready():
    """Readiness probe — checks critical dependencies."""
    checks = {}
    overall = "ok"

    # Check Supabase
    try:
        from app.db.supabase_client import get_supabase_client
        client = get_supabase_client()
        if client:
            checks["supabase"] = "ok"
        else:
            checks["supabase"] = "unavailable"
            overall = "degraded"
    except Exception as e:
        checks["supabase"] = f"error: {type(e).__name__}"
        overall = "degraded"

    # Check Gemini LLM API key configured in .env
    if settings.effective_gemini_api_key and settings.effective_gemini_api_key != "your-gemini-api-key":
        checks["llm"] = f"gemini ({settings.active_llm_model})"
    else:
        checks["llm"] = "gemini_key_not_configured"
        overall = "degraded"

    # Check Pinecone
    try:
        from app.external.pinecone_client import get_pinecone_index
        idx = get_pinecone_index()
        if idx:
            checks["pinecone"] = "ok"
        else:
            checks["pinecone"] = "unavailable"
            overall = "degraded"
    except Exception as e:
        checks["pinecone"] = f"error: {type(e).__name__}"
        overall = "degraded"

    # Check reranker model availability
    try:
        from sentence_transformers import CrossEncoder
        checks["reranker"] = "available"
    except Exception:
        checks["reranker"] = "unavailable"
        overall = "degraded"

    return {"status": overall, "checks": checks}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)