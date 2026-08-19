import hashlib
from typing import Union

def compute_sha256(data: Union[str, bytes]) -> str:
    """Compute SHA256 hex digest for string or byte input."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()

def compute_md5(data: Union[str, bytes]) -> str:
    """Compute MD5 hex digest for caching keys."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.md5(data).hexdigest()
