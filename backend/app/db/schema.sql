-- ============================================================
-- Supabase Database Schema for Fine-Explain RAG Architecture
-- Execute this script in Supabase SQL Editor (SQL Editor -> New Query)
-- ============================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 1. USERS TABLE
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. PRODUCTS TABLE
CREATE TABLE IF NOT EXISTS public.products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    issuer VARCHAR(255) NOT NULL,
    effective_date DATE NOT NULL,
    user_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. DOCUMENTS TABLE
CREATE TABLE IF NOT EXISTS public.documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES public.products(id) ON DELETE CASCADE,
    file_name VARCHAR(255) NOT NULL,
    file_hash VARCHAR(64) UNIQUE NOT NULL,
    s3_key VARCHAR(512),
    total_pages INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'uploaded',
    upload_date TIMESTAMPTZ DEFAULT NOW()
);

-- 4. CHUNKS TABLE (Metadata store alongside Pinecone vector index)
CREATE TABLE IF NOT EXISTS public.chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES public.documents(id) ON DELETE CASCADE,
    parent_chunk_id UUID,
    section_name VARCHAR(255),
    page_number INTEGER,
    text TEXT NOT NULL,
    token_count INTEGER,
    embedding_id VARCHAR(255),
    search_vector tsvector GENERATED ALWAYS AS (to_tsvector('english', text)) STORED,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for BM25 / PostgreSQL Full-Text Search
CREATE INDEX IF NOT EXISTS idx_chunks_search_vector ON public.chunks USING GIN (search_vector);
CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON public.chunks(document_id);

-- 5. HILT TASKS TABLE (Human-in-the-Loop)
CREATE TABLE IF NOT EXISTS public.hilt_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    task_type VARCHAR(50) NOT NULL,
    payload JSONB NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    resolution_data JSONB,
    resolver_user_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

-- 6. VERIFIED ANSWERS TABLE (Feedback Loop & Evaluation)
CREATE TABLE IF NOT EXISTS public.verified_answers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_query TEXT NOT NULL,
    context_hash VARCHAR(64),
    final_answer TEXT NOT NULL,
    source_citations JSONB DEFAULT '[]'::jsonb,
    confidence_score FLOAT,
    verified_by_user_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. SCENARIOS TABLE
CREATE TABLE IF NOT EXISTS public.scenarios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    user_id UUID,
    principal NUMERIC(15, 2) NOT NULL,
    duration_months INTEGER NOT NULL,
    interest_rate NUMERIC(5, 2),
    parameters JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
