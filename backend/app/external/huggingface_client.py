"""
Hugging Face Cloud API Client for FinExplain.

Strictly uses Hugging Face Cloud Inference API (all-MiniLM-L6-v2) for embeddings.
NEVER loads local PyTorch / SentenceTransformer models to ensure lightweight,
zero-CPU, zero-memory execution on Render free-tier environments.
"""

import os
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional
import numpy as np

from app.core.config import settings

logger = logging.getLogger(__name__)

_hf_client = None
_pool = ThreadPoolExecutor(max_workers=8, thread_name_prefix="hf_embedder")
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def get_hf_token() -> Optional[str]:
    """Retrieve Hugging Face API token from settings or environment."""
    return (
        settings.HUGGINGFACE_API_KEY
        or settings.HF_TOKEN
        or os.getenv("HUGGINGFACE_API_KEY")
        or os.getenv("HF_TOKEN")
    )


def get_hf_inference_client():
    """Get or initialize Hugging Face InferenceClient."""
    global _hf_client
    if _hf_client is None:
        try:
            from huggingface_hub import InferenceClient
            token = get_hf_token()
            _hf_client = InferenceClient(token=token)
        except Exception as e:
            logger.error(f"[HFClient] Could not initialize HuggingFace InferenceClient: {e}")
            _hf_client = None
    return _hf_client


def _embed_single_text(text: str, model_name: str) -> List[float]:
    """Embed a single text string via Hugging Face Cloud Inference API."""
    client = get_hf_inference_client()
    if not client:
        raise RuntimeError("Hugging Face InferenceClient is not configured or token is missing.")

    res = client.feature_extraction(text, model=model_name)
    arr = np.array(res)
    if arr.ndim > 1:
        arr = np.mean(arr, axis=0)
    return arr.tolist()


def generate_hf_embeddings(
    texts: List[str],
    model_name: Optional[str] = None
) -> List[List[float]]:
    """
    Generate embeddings for a list of texts via Hugging Face Cloud Inference API.
    Uses multi-threaded worker pool for fast parallel API requests without local CPU overhead.
    """
    if not texts:
        return []

    target_model = model_name or MODEL_NAME

    if len(texts) == 1:
        return [_embed_single_text(texts[0], target_model)]

    # Parallelize feature extraction calls across worker pool
    futures = [_pool.submit(_embed_single_text, t, target_model) for t in texts]
    results = [f.result() for f in futures]
    return results


def generate_hf_embedding(
    text: str,
    model_name: Optional[str] = None
) -> List[float]:
    """Generate embedding for a single text string via Hugging Face Cloud API."""
    if not text:
        return [0.0] * 384
    return _embed_single_text(text, model_name or MODEL_NAME)


def get_sentence_transformer(model_name: Optional[str] = None):
    """Compatibility interface returning the Hugging Face Cloud client."""
    return get_hf_inference_client()
