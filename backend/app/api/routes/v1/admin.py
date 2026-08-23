"""
Admin API Endpoints.

Provides platform-wide administration capabilities:
- User management (list, search, role assignment, deletion)
- Document and product oversight
- HITL task management
- System health monitoring
- Platform analytics

All endpoints require admin role authorization.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging

from app.auth.jwt_handler import get_current_user
from app.db.supabase_client import get_supabase_client
from app.db.repositories.user_repo import (
    get_user_role,
    get_all_users,
    count_all_users,
    get_user_by_id,
    update_user_role,
    delete_user,
)
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Admin authorization dependency
# ---------------------------------------------------------------------------

def require_admin(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Dependency that ensures the authenticated user has admin role."""
    user_id = current_user.get("id")
    email = current_user.get("email", "")
    role = get_user_role(user_id, email=email)
    if role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required. You do not have permission to access this resource.",
        )
    current_user["role"] = "admin"
    return current_user


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class UpdateRoleRequest(BaseModel):
    role: str  # "admin" or "user"


class ResolveTaskRequest(BaseModel):
    resolution: str
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Platform Statistics
# ---------------------------------------------------------------------------

@router.get("/stats")
def get_platform_stats(admin: Dict[str, Any] = Depends(require_admin)):
    """Get platform-wide statistics."""
    supabase = get_supabase_client()
    stats = {}

    try:
        # Users count
        res = supabase.table("users").select("id", count="exact").execute()
        stats["total_users"] = res.count if hasattr(res, "count") and res.count is not None else len(res.data or [])
    except Exception:
        stats["total_users"] = 0

    try:
        # Products count
        res = supabase.table("products").select("id", count="exact").execute()
        stats["total_products"] = res.count if hasattr(res, "count") and res.count is not None else len(res.data or [])
    except Exception:
        stats["total_products"] = 0

    try:
        # Documents count
        res = supabase.table("documents").select("id", count="exact").execute()
        stats["total_documents"] = res.count if hasattr(res, "count") and res.count is not None else len(res.data or [])
    except Exception:
        stats["total_documents"] = 0

    try:
        # Chunks count
        res = supabase.table("chunks").select("id", count="exact").execute()
        stats["total_chunks"] = res.count if hasattr(res, "count") and res.count is not None else len(res.data or [])
    except Exception:
        stats["total_chunks"] = 0

    try:
        # HITL tasks
        res = supabase.table("hilt_tasks").select("id, status").execute()
        tasks = res.data or []
        stats["total_hitl_tasks"] = len(tasks)
        stats["pending_hitl_tasks"] = sum(1 for t in tasks if t.get("status") == "pending")
        stats["resolved_hitl_tasks"] = sum(1 for t in tasks if t.get("status") == "resolved")
    except Exception:
        stats["total_hitl_tasks"] = 0
        stats["pending_hitl_tasks"] = 0
        stats["resolved_hitl_tasks"] = 0

    try:
        # Feedback (verified_answers) count
        res = supabase.table("verified_answers").select("id", count="exact").execute()
        stats["total_feedback"] = res.count if hasattr(res, "count") and res.count is not None else len(res.data or [])
    except Exception:
        stats["total_feedback"] = 0

    try:
        # Scenarios count
        res = supabase.table("scenarios").select("id", count="exact").execute()
        stats["total_scenarios"] = res.count if hasattr(res, "count") and res.count is not None else len(res.data or [])
    except Exception:
        stats["total_scenarios"] = 0

    return stats


# ---------------------------------------------------------------------------
# User Management
# ---------------------------------------------------------------------------

@router.get("/users")
def list_users(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    admin: Dict[str, Any] = Depends(require_admin),
):
    """List all users with pagination and optional search."""
    users = get_all_users(limit=limit, offset=offset, search=search)
    total = count_all_users()
    return {"users": users, "total": total, "limit": limit, "offset": offset}


@router.get("/users/{user_id}")
def get_user_detail(user_id: str, admin: Dict[str, Any] = Depends(require_admin)):
    """Get detailed information about a specific user."""
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Remove sensitive fields
    user.pop("hashed_password", None)

    # Enrich with role
    role = get_user_role(user_id)
    user["role"] = role

    # Get user's products and documents count
    supabase = get_supabase_client()
    try:
        prods = supabase.table("products").select("id", count="exact").eq("user_id", user_id).execute()
        user["products_count"] = prods.count if hasattr(prods, "count") and prods.count is not None else len(prods.data or [])
    except Exception:
        user["products_count"] = 0

    return user


@router.put("/users/{user_id}/role")
def change_user_role(
    user_id: str,
    req: UpdateRoleRequest,
    admin: Dict[str, Any] = Depends(require_admin),
):
    """Change a user's role (admin/user)."""
    if req.role not in ("admin", "user"):
        raise HTTPException(status_code=400, detail="Role must be 'admin' or 'user'")

    # Prevent admin from demoting themselves
    if user_id == admin["id"] and req.role != "admin":
        raise HTTPException(status_code=400, detail="You cannot remove your own admin privileges")

    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    success = update_user_role(user_id, req.role)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update user role")

    return {"message": f"User role updated to '{req.role}'", "user_id": user_id, "role": req.role}


@router.delete("/users/{user_id}")
def remove_user(user_id: str, admin: Dict[str, Any] = Depends(require_admin)):
    """Delete a user account."""
    if user_id == admin["id"]:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")

    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    success = delete_user(user_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete user")

    return {"message": "User deleted successfully", "user_id": user_id}


# ---------------------------------------------------------------------------
# Document Management
# ---------------------------------------------------------------------------

@router.get("/documents")
def list_all_documents(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    admin: Dict[str, Any] = Depends(require_admin),
):
    """List all documents across all users."""
    supabase = get_supabase_client()

    try:
        # Get documents with product info
        docs_res = (
            supabase.table("documents")
            .select("*")
            .order("upload_date", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        docs = docs_res.data or []

        # Enrich with product names
        product_ids = list(set(d.get("product_id") for d in docs if d.get("product_id")))
        if product_ids:
            prods_res = supabase.table("products").select("id, name, issuer, user_id").in_("id", product_ids).execute()
            prod_map = {p["id"]: p for p in (prods_res.data or [])}
            for d in docs:
                prod = prod_map.get(d.get("product_id"), {})
                d["product_name"] = prod.get("name", "Unknown")
                d["issuer"] = prod.get("issuer", "Unknown")
                d["owner_user_id"] = prod.get("user_id")

        # Total count
        count_res = supabase.table("documents").select("id", count="exact").execute()
        total = count_res.count if hasattr(count_res, "count") and count_res.count is not None else len(docs)

        return {"documents": docs, "total": total, "limit": limit, "offset": offset}
    except Exception as e:
        logger.error(f"Admin documents listing error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch documents")


@router.delete("/documents/{document_id}")
def admin_delete_document(document_id: str, admin: Dict[str, Any] = Depends(require_admin)):
    """Delete any document (admin override, no ownership check)."""
    supabase = get_supabase_client()
    try:
        # Check exists
        res = supabase.table("documents").select("id").eq("id", document_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Document not found")

        supabase.table("documents").delete().eq("id", document_id).execute()
        return {"message": "Document deleted successfully", "document_id": document_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin document deletion error: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete document")


# ---------------------------------------------------------------------------
# Product Management
# ---------------------------------------------------------------------------

@router.get("/products")
def list_all_products(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    admin: Dict[str, Any] = Depends(require_admin),
):
    """List all products across all users."""
    supabase = get_supabase_client()
    try:
        prods_res = (
            supabase.table("products")
            .select("*")
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        products = prods_res.data or []

        # Enrich with document count per product
        for p in products:
            try:
                doc_res = supabase.table("documents").select("id", count="exact").eq("product_id", p["id"]).execute()
                p["document_count"] = doc_res.count if hasattr(doc_res, "count") and doc_res.count is not None else len(doc_res.data or [])
            except Exception:
                p["document_count"] = 0

        # Enrich with owner email
        user_ids = list(set(p.get("user_id") for p in products if p.get("user_id")))
        if user_ids:
            users_res = supabase.table("users").select("id, email, full_name").in_("id", user_ids).execute()
            user_map = {u["id"]: u for u in (users_res.data or [])}
            for p in products:
                owner = user_map.get(p.get("user_id"), {})
                p["owner_email"] = owner.get("email", "Unknown")
                p["owner_name"] = owner.get("full_name", "Unknown")

        count_res = supabase.table("products").select("id", count="exact").execute()
        total = count_res.count if hasattr(count_res, "count") and count_res.count is not None else len(products)

        return {"products": products, "total": total, "limit": limit, "offset": offset}
    except Exception as e:
        logger.error(f"Admin products listing error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch products")


@router.delete("/products/{product_id}")
def admin_delete_product(product_id: str, admin: Dict[str, Any] = Depends(require_admin)):
    """Delete any product (admin override)."""
    supabase = get_supabase_client()
    try:
        res = supabase.table("products").select("id").eq("id", product_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Product not found")

        supabase.table("products").delete().eq("id", product_id).execute()
        return {"message": "Product deleted successfully", "product_id": product_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin product deletion error: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete product")


# ---------------------------------------------------------------------------
# HITL Task Management
# ---------------------------------------------------------------------------

@router.get("/hitl-tasks")
def list_all_hitl_tasks(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    admin: Dict[str, Any] = Depends(require_admin),
):
    """List all HITL tasks across all users."""
    supabase = get_supabase_client()
    try:
        query = supabase.table("hilt_tasks").select("*").order("created_at", desc=True)
        if status_filter:
            query = query.eq("status", status_filter)
        query = query.range(offset, offset + limit - 1)
        res = query.execute()
        tasks = res.data or []

        count_query = supabase.table("hilt_tasks").select("id", count="exact")
        if status_filter:
            count_query = count_query.eq("status", status_filter)
        count_res = count_query.execute()
        total = count_res.count if hasattr(count_res, "count") and count_res.count is not None else len(tasks)

        return {"tasks": tasks, "total": total, "limit": limit, "offset": offset}
    except Exception as e:
        logger.error(f"Admin HITL tasks listing error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch HITL tasks")


@router.post("/hitl-tasks/{task_id}/resolve")
def admin_resolve_hitl_task(
    task_id: str,
    req: ResolveTaskRequest,
    admin: Dict[str, Any] = Depends(require_admin),
):
    """Admin-resolve any HITL task."""
    supabase = get_supabase_client()
    try:
        res = supabase.table("hilt_tasks").select("id, status").eq("id", task_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="HITL task not found")

        from datetime import datetime
        update_data = {
            "status": "resolved",
            "resolution_data": {
                "resolution": req.resolution,
                "notes": req.notes,
                "resolved_by": admin["email"],
                "admin_resolved": True,
            },
            "resolver_user_id": admin["id"],
            "resolved_at": datetime.utcnow().isoformat(),
        }
        supabase.table("hilt_tasks").update(update_data).eq("id", task_id).execute()
        return {"message": "HITL task resolved by admin", "task_id": task_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin HITL resolve error: {e}")
        raise HTTPException(status_code=500, detail="Failed to resolve HITL task")


# ---------------------------------------------------------------------------
# Feedback Management
# ---------------------------------------------------------------------------

@router.get("/feedback")
def list_all_feedback(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    admin: Dict[str, Any] = Depends(require_admin),
):
    """List all user feedback entries (verified_answers table)."""
    supabase = get_supabase_client()
    try:
        res = (
            supabase.table("verified_answers")
            .select("*")
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        feedback = res.data or []

        count_res = supabase.table("verified_answers").select("id", count="exact").execute()
        total = count_res.count if hasattr(count_res, "count") and count_res.count is not None else len(feedback)

        return {"feedback": feedback, "total": total, "limit": limit, "offset": offset}
    except Exception as e:
        logger.error(f"Admin feedback listing error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch feedback")


# ---------------------------------------------------------------------------
# Extended System Health
# ---------------------------------------------------------------------------

@router.get("/health")
async def admin_health_check(admin: Dict[str, Any] = Depends(require_admin)):
    """Extended health check with detailed component status."""
    checks = {}
    overall = "ok"

    # Supabase
    try:
        supabase = get_supabase_client()
        res = supabase.table("users").select("id").limit(1).execute()
        checks["supabase"] = {"status": "ok", "detail": "Connected"}
    except Exception as e:
        checks["supabase"] = {"status": "error", "detail": str(e)[:100]}
        overall = "degraded"

    # Gemini LLM
    api_key = settings.effective_gemini_api_key
    if api_key and api_key != "your-gemini-api-key":
        checks["llm"] = {
            "status": "ok",
            "detail": f"{settings.LLM_PROVIDER} ({settings.active_llm_model})",
            "provider": settings.LLM_PROVIDER,
            "model": settings.active_llm_model,
        }
    else:
        checks["llm"] = {"status": "error", "detail": "API key not configured"}
        overall = "degraded"

    # Pinecone
    try:
        from app.external.pinecone_client import get_pinecone_index
        idx = get_pinecone_index()
        if idx:
            checks["pinecone"] = {"status": "ok", "detail": f"Index: {settings.PINECONE_INDEX_NAME}"}
        else:
            checks["pinecone"] = {"status": "unavailable", "detail": "Index not found"}
            overall = "degraded"
    except Exception as e:
        checks["pinecone"] = {"status": "error", "detail": str(e)[:100]}
        overall = "degraded"

    # Redis
    try:
        if settings.REDIS_URL and "localhost" not in settings.REDIS_URL:
            checks["redis"] = {"status": "configured", "detail": "Upstash Redis configured"}
        else:
            checks["redis"] = {"status": "local", "detail": settings.REDIS_URL or "Not configured"}
    except Exception:
        checks["redis"] = {"status": "unknown", "detail": "Unable to check"}

    # Embeddings model
    try:
        from app.external.huggingface_client import get_sentence_transformer
        model = get_sentence_transformer()
        checks["embeddings"] = {"status": "ok", "detail": settings.HF_EMBEDDING_MODEL}
    except Exception as e:
        checks["embeddings"] = {"status": "error", "detail": str(e)[:100]}
        overall = "degraded"

    # Reranker
    try:
        from sentence_transformers import CrossEncoder
        checks["reranker"] = {"status": "ok", "detail": "CrossEncoder available"}
    except Exception:
        checks["reranker"] = {"status": "unavailable", "detail": "Not installed"}
        overall = "degraded"

    return {
        "status": overall,
        "environment": settings.ENVIRONMENT,
        "checks": checks,
    }
