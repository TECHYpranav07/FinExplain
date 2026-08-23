"""
Embedding Interface for FinExplain.

Strictly delegates embedding generation to Hugging Face Cloud Inference API.
No local model loading.
"""
from typing import List, Optional
from app.external.huggingface_client import (
    generate_hf_embeddings,
    generate_hf_embedding,
)


def generate_embeddings(texts: List[str], model_name: Optional[str] = None) -> List[List[float]]:
    """Generate embeddings for a list of text chunks via Hugging Face Cloud API."""
    return generate_hf_embeddings(texts, model_name=model_name)


def generate_embedding(text: str, model_name: Optional[str] = None) -> List[float]:
    """Generate embedding for a single text string via Hugging Face Cloud API."""
    return generate_hf_embedding(text, model_name=model_name)