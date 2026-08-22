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

from app.api.routes.v1 import documents, queries, hilt, products, feedback, analysis

app = FastAPI(
    title="FinExplain API",
    description="Evidence-first AI for loan decisions",
    version="1.0.0"
)

# Enable CORS with configured origins (FIN-004: no more wildcard)
_cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Register all route handlers
app.include_router(documents.router, prefix="/api/v1/documents", tags=["Documents"])
app.include_router(queries.router, prefix="/api/v1/queries", tags=["Queries"])
app.include_router(hilt.router, prefix="/api/v1/hilt", tags=["HILT"])
app.include_router(products.router, prefix="/api/v1/products", tags=["Products"])
app.include_router(feedback.router, prefix="/api/v1/feedback", tags=["Feedback"])
app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["Analysis"])

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