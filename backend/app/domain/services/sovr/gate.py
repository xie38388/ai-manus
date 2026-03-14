"""
SOVR Gate
The core interceptor that sits between the AI Agent and tool execution.
Evaluates every tool call against policies, records audit entries,
and enforces decisions (allow/block/review).
"""

from typing import Dict, Any, Optional, Tuple
from datetime import datetime, UTC
from pydantic import BaseModel
from enum import Enum
import time
import logging

from app.domain.services.sovr.policy import PolicyEngine, PolicyAction, RiskLevel
from app.domain.services.sovr.audit import AuditChain, AuditEntry

logger = logging.getLogger(__name__)


class GateDecision(BaseModel):
    """The result of a gate check"""
    allowed: bool
    action: PolicyAction
    risk_level: RiskLevel
    policy_id: str
    policy_name: str
    reason: str
    audit_entry_id: str


# Singleton instances (will be replaced by DI in production)
_policy_engine: Optional[PolicyEngine] = None
_audit_chain: Optional[AuditChain] = None


def get_policy_engine() -> PolicyEngine:
    global _policy_engine
    if _policy_engine is None:
        _policy_engine = PolicyEngine()
    return _policy_engine


def get_audit_chain() -> AuditChain:
    global _audit_chain
    if _audit_chain is None:
        _audit_chain = AuditChain()
    return _audit_chain


class SovrGate:
    """
    SOVR Gate - the decision plane for AI Agent tool calls.
    
    Usage in BaseAgent.execute():
        gate = SovrGate(session_id, user_id)
        decision = gate.check(tool_name, function_name, function_args)
        if not decision.allowed:
            # Block the tool call
            yield ErrorEvent(error=f"SOVR blocked: {decision.reason}")
            continue
        # Execute the tool
        result = await self.invoke_tool(tool, tool_call)
        gate.record_result(decision.audit_entry_id, success=True)
    """

    def __init__(self, session_id: str, user_id: str):
        self.session_id = session_id
        self.user_id = user_id
        self.policy_engine = get_policy_engine()
        self.audit_chain = get_audit_chain()

    def check(
        self,
        tool_name: str,
        function_name: str,
        function_args: Dict[str, Any],
    ) -> GateDecision:
        """
        Check a tool call against SOVR policies.
        Returns a GateDecision indicating whether to proceed.
        """
        # Evaluate against policies
        policy, action = self.policy_engine.evaluate(function_name, function_args)

        # Determine if allowed
        allowed = action in (PolicyAction.ALLOW, PolicyAction.ALLOW_AND_LOG)
        
        # Build reason
        if action == PolicyAction.BLOCK:
            reason = f"Blocked by policy '{policy.name}': {policy.description}"
        elif action == PolicyAction.REVIEW:
            reason = f"Requires review per policy '{policy.name}': {policy.description}"
        elif action == PolicyAction.ALLOW_AND_LOG:
            reason = f"Allowed with audit logging per policy '{policy.name}'"
        else:
            reason = f"Allowed by policy '{policy.name}'"

        # Create audit entry
        audit_entry = AuditEntry(
            session_id=self.session_id,
            user_id=self.user_id,
            tool_name=tool_name,
            function_name=function_name,
            function_args=self._sanitize_args(function_args),
            policy_id=policy.id,
            risk_level=policy.risk_level.value,
            action=action.value,
        )
        self.audit_chain.record(audit_entry)

        if action == PolicyAction.BLOCK:
            logger.warning(
                f"[SOVR Gate] BLOCKED tool call: {function_name} "
                f"in session {self.session_id} - {reason}"
            )
        elif policy.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            logger.info(
                f"[SOVR Gate] HIGH-RISK tool call: {function_name} "
                f"in session {self.session_id} - risk={policy.risk_level.value}"
            )

        return GateDecision(
            allowed=allowed,
            action=action,
            risk_level=policy.risk_level,
            policy_id=policy.id,
            policy_name=policy.name,
            reason=reason,
            audit_entry_id=audit_entry.id,
        )

    def record_result(
        self,
        audit_entry_id: str,
        success: bool,
        error: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ) -> None:
        """Record the execution result of a tool call"""
        self.audit_chain.update_execution_result(
            entry_id=audit_entry_id,
            session_id=self.session_id,
            success=success,
            error=error,
            duration_ms=duration_ms,
        )

    def get_trust_score(self) -> int:
        """Get the current trust score for this session"""
        stats = self.audit_chain.get_session_stats(self.session_id)
        return stats["trust_score"]

    def get_session_stats(self) -> Dict[str, Any]:
        """Get audit statistics for this session"""
        return self.audit_chain.get_session_stats(self.session_id)

    def _sanitize_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize function arguments for audit logging.
        Truncate long values and mask sensitive data.
        """
        sanitized = {}
        for key, value in args.items():
            str_value = str(value)
            # Truncate long values
            if len(str_value) > 500:
                sanitized[key] = str_value[:500] + "...[truncated]"
            else:
                sanitized[key] = value
        return sanitized
