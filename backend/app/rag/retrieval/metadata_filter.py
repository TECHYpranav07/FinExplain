from typing import List, Dict, Any, Optional

def apply_metadata_filters(
    chunks: List[Dict[str, Any]],
    product_ids: Optional[List[str]] = None,
    document_ids: Optional[List[str]] = None,
    min_page: Optional[int] = None,
    max_page: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Filters chunks based on product IDs, document IDs, or page range."""
    filtered = []
    for chunk in chunks:
        metadata = chunk.get("metadata") or {}
        # Check product filter
        if product_ids:
            chunk_pid = chunk.get("product_id") or metadata.get("product_id")
            if chunk_pid and chunk_pid not in product_ids:
                continue

        # Check document filter
        if document_ids:
            chunk_did = chunk.get("document_id") or metadata.get("document_id")
            if chunk_did and chunk_did not in document_ids:
                continue

        # Check page bounds
        page = chunk.get("page_number") or chunk.get("page_num")
        if page is not None:
            if min_page is not None and page < min_page:
                continue
            if max_page is not None and page > max_page:
                continue

        filtered.append(chunk)
    return filtered
