# FinExplain - Evidence-First AI for Financial & Loan Decisions

**FinExplain** is an advanced Agentic RAG (Retrieval-Augmented Generation) application designed to extract, analyze, and compare financial and loan policy documents. It provides evidence-first answers backed by verbatim citations, cross-encoder reranking, full-text BM25 hybrid search, and Human-in-the-Loop (HITL) conflict resolution.

---

## 🏗️ System Architecture

```
                               ┌──────────────────────┐
                               │   React Frontend     │
                               └──────────┬───────────┘
                                          │ HTTP / REST
                               ┌──────────▼───────────┐
                               │   FastAPI Backend    │
                               └──────────┬───────────┘
               ┌──────────────────────────┼──────────────────────────┐
               │                          │                          │
    ┌──────────▼───────────┐   ┌──────────▼───────────┐   ┌──────────▼───────────┐
    │  Supabase PostgreSQL │   │   Pinecone Vector    │   │    Groq Llama-3      │
    │   (Metadata & BM25)  │   │  (Dense Search 384d) │   │  (Evidence-First LLM)│
    └──────────────────────┘   └──────────────────────┘   └──────────────────────┘
```

---

## 🛠️ Technology Stack

- **Framework**: Python 3.11, [FastAPI](https://fastapi.tiangolo.com/), Pydantic v2
- **Relational Database**: [Supabase PostgreSQL](https://supabase.com/) (`supabase-py` SDK)
- **Vector Database**: [Pinecone](https://www.pinecone.io/) (`pinecone-client` v5 SDK)
- **Embeddings**: Sentence-Transformers (`all-MiniLM-L6-v2`, 384 dimensions)
- **Reranker**: Cross-Encoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`)
- **LLM Engine**: [Groq API](https://groq.com/) (`llama3-70b-8192`)
- **Async Queue & Cache**: Redis, Celery
- **PDF Parser**: PyMuPDF (`fitz`)

---

## 📂 Folder & File Structure

```
fine-explain/
├── Dockerfile
├── README.md
├── docker-compose.yml
├── requirements.txt
│
├── frontend/
│   └── .env.example
│
└── backend/
    ├── .env
    ├── .env.example
    │
    └── app/
        ├── api/                                    # REST Endpoints (FastAPI)
        │   ├── dependencies.py                     # Supabase & Auth Injection
        │   ├── schemas.py                          # Request / Response Schemas
        │   └── routes/v1/
        │       ├── documents.py                    # Document Ingestion API
        │       ├── queries.py                      # RAG Q&A API
        │       ├── hilt.py                         # Human-in-the-Loop Task API
        │       ├── products.py                     # Financial Products API
        │       └── feedback.py                     # User Feedback API
        │
        ├── core/                                   # App Configuration & System Settings
        │   ├── config.py                           # Pydantic Settings
        │   ├── security.py                         # Security & Authentication
        │   ├── exceptions.py                       # Custom Exceptions
        │   └── constants.py                        # Constants & Enums
        │
        ├── db/                                     # Supabase Database Layer
        │   ├── supabase_client.py                  # Singleton Supabase Client
        │   ├── schema.sql                          # Database DDL for Supabase SQL Editor
        │   └── repositories/                       # Data Repositories
        │       ├── product_repo.py
        │       ├── document_repo.py
        │       ├── chunk_repo.py                   # BM25 Full-Text Search
        │       ├── hilt_repo.py
        │       └── verified_answer_repo.py
        │
        ├── external/                               # External Clients
        │   ├── pinecone_client.py                  # Pinecone Vector Operations
        │   ├── groq_client.py                      # Groq Llama-3 API
        │   └── huggingface_client.py
        │
        ├── models/                                 # Pydantic Entity Models
        │   ├── user.py
        │   ├── product.py
        │   ├── document.py
        │   ├── chunk.py
        │   ├── hilt_task.py
        │   ├── verified_answer.py
        │   └── scenario.py
        │
        ├── rag/                                    # Core RAG Pipeline
        │   ├── orchestrator.py                     # Main RAG Pipeline Entry point
        │   ├── context/                            # Context Construction
        │   │   ├── builder.py                      # Token-budgeted context builder
        │   │   └── compressor.py
        │   ├── enhancement/                        # Query Transformation
        │   │   ├── intent_classifier.py
        │   │   ├── query_rewriter.py
        │   │   └── hyde_generator.py
        │   ├── generation/                         # LLM Invocation
        │   │   ├── generator.py                    # Evidence-First Groq Prompting
        │   │   └── prompt_templates.py
        │   ├── refind/                             # Corrective RAG Loop
        │   │   └── orchestrator.py
        │   ├── retrieval/                          # Hybrid Search Engine
        │   │   ├── dense_retriever.py              # Pinecone Vector Search
        │   │   ├── sparse_retriever.py             # Supabase BM25 tsvector Search
        │   │   ├── hybrid_retriever.py             # Reciprocal Rank Fusion (RRF)
        │   │   └── reranker.py                     # Cross-Encoder Reranking
        │   └── verification/                       # Grounding & Verification
        │       └── grounder.py                     # Citation verification & confidence
        │
        ├── ingestion/                              # Document Pipeline
        │   ├── parser.py                           # PyMuPDF PDF Parsing
        │   ├── chunker.py                          # Hierarchical Splitter
        │   ├── embedder.py                         # SentenceTransformers Embedding
        │   └── pipeline.py                         # Full Ingestion Workflow
        │
        └── main.py                                 # FastAPI Server Entry point
```

---

## ⚙️ Environment Variables Setup

Create a `.env` file inside the `backend/` directory based on [`backend/.env.example`](file:///d:/Projects/fine-explain/backend/.env.example):

```env
# Supabase Configuration
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_KEY=your-supabase-anon-or-service-role-key

# Pinecone Vector Database Configuration
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_INDEX_NAME=fine-explain

# Groq LLM Engine
GROQ_API_KEY=your-groq-api-key

# Redis (Optional for caching)
REDIS_URL=redis://localhost:6379/0
```

---

## 🗄️ Database Setup (Supabase)

1. Navigate to your **Supabase Dashboard** -> **SQL Editor**.
2. Create a **New Query**.
3. Copy the SQL definitions from [`backend/app/db/schema.sql`](file:///d:/Projects/fine-explain/backend/app/db/schema.sql) and run it. This creates:
   - `users`, `products`, `documents`, `chunks`, `hilt_tasks`, `verified_answers`, and `scenarios` tables.
   - The PostgreSQL BM25 `tsvector` full-text search index (`idx_chunks_tsv`).

---

## 🚀 Running the Application Locally

### 1. Activate Virtual Environment & Install Dependencies
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Start Backend Server
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Open API Documentation
Once the server is running, visit:
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 📌 Features Implemented

- ✅ **Hybrid Search**: Combines Pinecone dense vector embeddings with Supabase PostgreSQL BM25 full-text search using Reciprocal Rank Fusion (RRF).
- ✅ **Cross-Encoder Reranking**: Re-ranks retrieved chunks using `cross-encoder/ms-marco-MiniLM-L-6-v2` for precise relevance.
- ✅ **Document Ingestion Pipeline**: Parses PDFs (PyMuPDF), creates hierarchical parent-child chunks, generates embeddings, and indexes into Pinecone & Supabase.
- ✅ **Corrective RAG & Verification**: Computes citation coverage, verifies grounded claims, and computes confidence scores.
- ✅ **FastAPI Integration**: Clean REST API endpoints for document upload, Q&A queries, product metadata, and human-in-the-loop task handling.
#   F i n E x p l a i n  
 #   F i n E x p l a i n  
 