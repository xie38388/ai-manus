"""
SOVR API Routes
Exposes trust score, audit stats, and session audit entries to the frontend.
"""

from fastapi import APIRouter, Depends
from app.interfaces.api.dependencies import get_current_user
from app.domain.models.user import User
from app.interfaces.api.response import APIResponse
from app.domain.services.sovr.gate import get_audit_chain

router = APIRouter(prefix="/sovr", tags=["sovr"])


@router.get("/stats", response_model=APIResponse[dict])
async def get_global_stats(
    current_user: User = Depends(get_current_user),
) -> APIResponse[dict]:
    """Get global SOVR audit statistics"""
    audit_chain = get_audit_chain()
    stats = audit_chain.get_all_stats()
    return APIResponse.success(stats)


@router.get("/session/{session_id}/stats", response_model=APIResponse[dict])
async def get_session_stats(
    session_id: str,
    current_user: User = Depends(get_current_user),
) -> APIResponse[dict]:
    """Get SOVR audit statistics for a specific session"""
    audit_chain = get_audit_chain()
    stats = audit_chain.get_session_stats(session_id)
    return APIResponse.success(stats)


@router.get("/session/{session_id}/entries", response_model=APIResponse[list])
async def get_session_entries(
    session_id: str,
    current_user: User = Depends(get_current_user),
) -> APIResponse[list]:
    """Get all audit entries for a specific session"""
    audit_chain = get_audit_chain()
    entries = audit_chain.get_session_entries(session_id)
    return APIResponse.success([entry.model_dump() for entry in entries])


@router.get("/session/{session_id}/trust-score", response_model=APIResponse[dict])
async def get_trust_score(
    session_id: str,
    current_user: User = Depends(get_current_user),
) -> APIResponse[dict]:
    """Get trust score for a specific session"""
    audit_chain = get_audit_chain()
    stats = audit_chain.get_session_stats(session_id)
    return APIResponse.success({
        "trust_score": stats["trust_score"],
        "total_calls": stats["total_calls"],
        "blocked": stats["blocked"],
    })


@router.get("/session/{session_id}/verify", response_model=APIResponse[dict])
async def verify_chain_integrity(
    session_id: str,
    current_user: User = Depends(get_current_user),
) -> APIResponse[dict]:
    """Verify the hash chain integrity for a session"""
    audit_chain = get_audit_chain()
    is_valid = audit_chain.verify_chain_integrity(session_id)
    return APIResponse.success({
        "session_id": session_id,
        "chain_valid": is_valid,
    })
