"""
SOVR Audit Chain
Records every tool call decision for traceability and accountability.
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime, UTC
from enum import Enum
import hashlib
import json
import uuid
import logging

logger = logging.getLogger(__name__)


class AuditEntry(BaseModel):
    """A single audit record for a tool call decision"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    
    # Context
    session_id: str
    user_id: str
    
    # Tool call details
    tool_name: str
    function_name: str
    function_args: Dict[str, Any]
    
    # SOVR decision
    policy_id: str
    risk_level: str
    action: str  # allow, allow_and_log, review, block
    
    # Result (filled after execution)
    executed: bool = False
    execution_success: Optional[bool] = None
    execution_error: Optional[str] = None
    execution_duration_ms: Optional[int] = None
    
    # Hash chain
    previous_hash: Optional[str] = None
    entry_hash: Optional[str] = None

    def compute_hash(self) -> str:
        """Compute SHA-256 hash of this entry for chain integrity"""
        data = {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "session_id": self.session_id,
            "user_id": self.user_id,
            "tool_name": self.tool_name,
            "function_name": self.function_name,
            "function_args": self.function_args,
            "policy_id": self.policy_id,
            "risk_level": self.risk_level,
            "action": self.action,
            "previous_hash": self.previous_hash or "genesis",
        }
        raw = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()


class AuditChain:
    """
    In-memory audit chain with hash-linked entries.
    Provides tamper-evident logging for all SOVR decisions.
    
    In production, this would be backed by MongoDB or a dedicated audit store.
    """

    def __init__(self):
        self._entries: Dict[str, List[AuditEntry]] = {}  # session_id -> entries
        self._latest_hash: Dict[str, str] = {}  # session_id -> latest hash

    def record(self, entry: AuditEntry) -> AuditEntry:
        """Record a new audit entry and link it to the chain"""
        session_id = entry.session_id
        
        # Link to previous entry
        entry.previous_hash = self._latest_hash.get(session_id)
        entry.entry_hash = entry.compute_hash()
        
        # Store
        if session_id not in self._entries:
            self._entries[session_id] = []
        self._entries[session_id].append(entry)
        self._latest_hash[session_id] = entry.entry_hash
        
        logger.info(
            f"[SOVR Audit] session={session_id} "
            f"tool={entry.function_name} "
            f"risk={entry.risk_level} "
            f"action={entry.action} "
            f"hash={entry.entry_hash[:12]}..."
        )
        
        return entry

    def update_execution_result(
        self,
        entry_id: str,
        session_id: str,
        success: bool,
        error: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ) -> None:
        """Update an audit entry with execution results"""
        entries = self._entries.get(session_id, [])
        for entry in entries:
            if entry.id == entry_id:
                entry.executed = True
                entry.execution_success = success
                entry.execution_error = error
                entry.execution_duration_ms = duration_ms
                return
        logger.warning(f"[SOVR Audit] Entry {entry_id} not found in session {session_id}")

    def get_session_entries(self, session_id: str) -> List[AuditEntry]:
        """Get all audit entries for a session"""
        return self._entries.get(session_id, [])

    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get summary statistics for a session"""
        entries = self._entries.get(session_id, [])
        if not entries:
            return {
                "total_calls": 0,
                "allowed": 0,
                "blocked": 0,
                "risk_breakdown": {},
                "trust_score": 100,
            }

        total = len(entries)
        allowed = sum(1 for e in entries if e.action in ("allow", "allow_and_log"))
        blocked = sum(1 for e in entries if e.action == "block")
        reviewed = sum(1 for e in entries if e.action == "review")
        
        risk_breakdown = {}
        for entry in entries:
            risk_breakdown[entry.risk_level] = risk_breakdown.get(entry.risk_level, 0) + 1

        # Trust score: starts at 100, decreases with high-risk and blocked operations
        trust_score = 100
        trust_score -= blocked * 15  # Each blocked operation costs 15 points
        trust_score -= risk_breakdown.get("critical", 0) * 10
        trust_score -= risk_breakdown.get("high", 0) * 3
        trust_score = max(0, min(100, trust_score))

        return {
            "total_calls": total,
            "allowed": allowed,
            "blocked": blocked,
            "reviewed": reviewed,
            "risk_breakdown": risk_breakdown,
            "trust_score": trust_score,
        }

    def verify_chain_integrity(self, session_id: str) -> bool:
        """Verify the hash chain integrity for a session"""
        entries = self._entries.get(session_id, [])
        if not entries:
            return True

        for i, entry in enumerate(entries):
            expected_hash = entry.compute_hash()
            if entry.entry_hash != expected_hash:
                logger.error(
                    f"[SOVR Audit] Chain integrity violation at entry {entry.id}: "
                    f"expected {expected_hash}, got {entry.entry_hash}"
                )
                return False

            if i > 0 and entry.previous_hash != entries[i - 1].entry_hash:
                logger.error(
                    f"[SOVR Audit] Chain link broken at entry {entry.id}: "
                    f"previous_hash mismatch"
                )
                return False

        return True

    def get_all_stats(self) -> Dict[str, Any]:
        """Get aggregate stats across all sessions"""
        total_sessions = len(self._entries)
        total_calls = sum(len(entries) for entries in self._entries.values())
        total_blocked = sum(
            sum(1 for e in entries if e.action == "block")
            for entries in self._entries.values()
        )
        
        return {
            "total_sessions": total_sessions,
            "total_calls": total_calls,
            "total_blocked": total_blocked,
            "avg_trust_score": (
                sum(
                    self.get_session_stats(sid)["trust_score"]
                    for sid in self._entries
                ) / total_sessions
                if total_sessions > 0
                else 100
            ),
        }
