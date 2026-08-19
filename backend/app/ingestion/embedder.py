from sentence_transformers import SentenceTransformer
from typing import List
import numpy as np

# Load the model once (all-MiniLM-L6-v2 - 384 dimensions)
_model = None

def get_embedder():
    global _model
    if _model is None:
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model

def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for a list of text chunks."""
    model = get_embedder()
    embeddings = model.encode(texts, convert_to_numpy=True)
    return embeddings.tolist()

def generate_embedding(text: str) -> List[float]:
    """Generate embedding for a single text string."""
    model = get_embedder()
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding.tolist()