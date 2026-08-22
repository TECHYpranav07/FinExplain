import os
os.environ["USE_TF"] = "0"
os.environ["USE_TORCH"] = "1"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

import logging
from typing import List, Optional
import requests
import numpy as np

from app.core.config import settings

logger = logging.getLogger(__name__)

_st_model = None
_ce_model = None
_hf_client = None


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
            logger.warning(f"Could not initialize HuggingFace InferenceClient: {e}")
            _hf_client = None
    return _hf_client


def get_sentence_transformer(model_name: str = "all-MiniLM-L6-v2"):
    """Local SentenceTransformer fallback."""
    global _st_model
    if _st_model is None:
        from sentence_transformers import SentenceTransformer
        _st_model = SentenceTransformer(model_name)
    return _st_model


def get_cross_encoder(model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
    """Local CrossEncoder reranker."""
    global _ce_model
    if _ce_model is None:
        from sentence_transformers import CrossEncoder
        _ce_model = CrossEncoder(model_name)
    return _ce_model


def generate_hf_embeddings_api(
    texts: List[str],
    model_name: Optional[str] = None
) -> Optional[List[List[float]]]:
    """
    Generate embeddings using Hugging Face Inference API via HTTP or InferenceClient.
    Returns None if API is unavailable or fails, allowing seamless fallback.
    """
    if not texts:
        return []

    model = model_name or settings.HF_EMBEDDING_MODEL or "sentence-transformers/all-MiniLM-L6-v2"
    token = get_hf_token()

    # Try via HTTP request first (efficient for batch embeddings)
    api_urls = [
        f"https://router.huggingface.co/hf-inference/models/{model}",
        f"https://api-inference.huggingface.co/pipeline/feature-extraction/{model}",
    ]

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    for api_url in api_urls:
        try:
            response = requests.post(
                api_url,
                headers=headers,
                json={"inputs": texts, "options": {"wait_for_model": True}},
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    # Check if output is shape (batch_size, seq_len, hidden_dim) or (batch_size, hidden_dim)
                    if isinstance(data[0], list):
                        if len(data[0]) > 0 and isinstance(data[0][0], list):
                            # Mean pooling across tokens
                            pooled = []
                            for item in data:
                                arr = np.array(item)
                                pooled.append(np.mean(arr, axis=0).tolist())
                            return pooled
                        return data
                    elif isinstance(data[0], (int, float)):
                        return [data]

            logger.debug(f"HF API returned status {response.status_code}: {response.text[:200]}")
        except Exception as e:
            logger.debug(f"HF API call to {api_url} failed: {e}")

    # Try via huggingface_hub InferenceClient
    try:
        client = get_hf_inference_client()
        if client:
            embeddings = []
            for text in texts:
                emb = client.feature_extraction(text, model=model)
                if isinstance(emb, np.ndarray):
                    if emb.ndim > 1:
                        emb = np.mean(emb, axis=0)
                    embeddings.append(emb.tolist())
                elif isinstance(emb, list):
                    if len(emb) > 0 and isinstance(emb[0], list):
                        embeddings.append(np.mean(np.array(emb), axis=0).tolist())
                    else:
                        embeddings.append(emb)
            if embeddings and len(embeddings) == len(texts):
                return embeddings
    except Exception as e:
        logger.debug(f"HF InferenceClient feature_extraction failed: {e}")

    return None


def generate_hf_embeddings(
    texts: List[str],
    model_name: Optional[str] = None
) -> List[List[float]]:
    """
    Generate embeddings using Hugging Face API first, with local fallback if needed.
    """
    if not texts:
        return []

    # 1. Try Hugging Face Inference API
    api_result = generate_hf_embeddings_api(texts, model_name=model_name)
    if api_result is not None and len(api_result) == len(texts):
        return api_result

    # 2. Fallback to local SentenceTransformer
    logger.info("Using local SentenceTransformer embedding model fallback.")
    model = get_sentence_transformer(model_name or "all-MiniLM-L6-v2")
    embeddings = model.encode(texts, convert_to_numpy=True)
    return embeddings.tolist()


def generate_hf_embedding(
    text: str,
    model_name: Optional[str] = None
) -> List[float]:
    """Generate embedding for a single text string."""
    results = generate_hf_embeddings([text], model_name=model_name)
    return results[0] if results else []
