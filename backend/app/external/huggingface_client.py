from sentence_transformers import SentenceTransformer, CrossEncoder
from typing import Optional

_st_model: Optional[SentenceTransformer] = None
_ce_model: Optional[CrossEncoder] = None

def get_sentence_transformer(model_name: str = "all-MiniLM-L6-v2") -> SentenceTransformer:
    global _st_model
    if _st_model is None:
        _st_model = SentenceTransformer(model_name)
    return _st_model

def get_cross_encoder(model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2") -> CrossEncoder:
    global _ce_model
    if _ce_model is None:
        _ce_model = CrossEncoder(model_name)
    return _ce_model
