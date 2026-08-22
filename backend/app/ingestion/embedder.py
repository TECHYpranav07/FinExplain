from typing import List, Optional
import numpy as np
from app.external.huggingface_client import (
    generate_hf_embeddings,
    generate_hf_embedding,
    get_sentence_transformer,
)

# Load the local model fallback once if needed
def get_embedder():
    return get_sentence_transformer()

def generate_embeddings(texts: List[str], model_name: Optional[str] = None) -> List[List[float]]:
    """
    Generate embeddings for a list of text chunks using Hugging Face API
    with local SentenceTransformer fallback.
    """
    return generate_hf_embeddings(texts, model_name=model_name)

def generate_embedding(text: str, model_name: Optional[str] = None) -> List[float]:
    """
    Generate embedding for a single text string using Hugging Face API
    with local SentenceTransformer fallback.
    """
    return generate_hf_embedding(text, model_name=model_name)