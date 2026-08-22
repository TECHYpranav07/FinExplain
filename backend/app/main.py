import os
os.environ["USE_TF"] = "0"
os.environ["USE_TORCH"] = "1"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from langsmith import Client
# Automatically traces LangChain calls if env vars are set

from app.api.routes.v1 import documents, queries, hilt, products, feedback, analysis

app = FastAPI(
    title="FinExplain API",
    description="Evidence-first AI for loan decisions",
    version="1.0.0"
)

# Enable CORS (so your React frontend can talk to this backend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    return HTMLResponse("<h1>FinExplain Frontend Console</h1><p>Run 'npm run build' in frontend/ to generate dist bundle.</p>")

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)