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
from fastapi.responses import FileResponse, HTMLResponse

@app.get("/", response_class=HTMLResponse)
async def root():
    frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend", "index.html")
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    return {"message": "FinExplain API is running", "status": "healthy"}

@app.get("/app", response_class=HTMLResponse)
async def serve_app():
    frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend", "index.html")
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    return HTMLResponse("<h1>FinExplain Frontend Console</h1><p>frontend/index.html not found.</p>")

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)