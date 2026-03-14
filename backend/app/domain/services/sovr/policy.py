"""
SOVR Policy Engine
Defines risk levels, policies, and decision rules for AI Agent tool calls.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from datetime import datetime, UTC
import logging
import re

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    """Risk classification for tool operations"""
    LOW = "low"          # Auto-approve: read operations, search
    MEDIUM = "medium"    # Log + proceed: file writes, browser navigation
    HIGH = "high"        # Require review: shell exec, file delete, external API
    CRITICAL = "critical"  # Block + alert: system commands, credential access


class PolicyAction(str, Enum):
    """Action to take based on policy evaluation"""
    ALLOW = "allow"           # Proceed immediately
    ALLOW_AND_LOG = "allow_and_log"  # Proceed but log for audit
    REVIEW = "review"         # Queue for human review (async)
    BLOCK = "block"           # Block immediately


class Policy(BaseModel):
    """A single policy rule"""
    id: str
    name: str
    description: str
    tool_pattern: str          # regex pattern matching tool/function names
    arg_patterns: Dict[str, str] = {}  # regex patterns for specific arguments
    risk_level: RiskLevel
    action: PolicyAction
    enabled: bool = True


# Default policy set - covers all ai-manus tools
DEFAULT_POLICIES: List[Policy] = [
    # === LOW RISK: Auto-approve ===
    Policy(
        id="read-file",
        name="Read File",
        description="Reading files is safe and non-destructive",
        tool_pattern=r"^(read_file|view_file|list_files|get_file_content)$",
        risk_level=RiskLevel.LOW,
        action=PolicyAction.ALLOW,
    ),
    Policy(
        id="search",
        name="Web Search",
        description="Search operations are read-only",
        tool_pattern=r"^(web_search|search)$",
        risk_level=RiskLevel.LOW,
        action=PolicyAction.ALLOW,
    ),
    Policy(
        id="browser-read",
        name="Browser Navigation",
        description="Navigating and reading web pages",
        tool_pattern=r"^(browser_navigate|browser_get_text|browser_read|browser_screenshot|browser_get_html)$",
        risk_level=RiskLevel.LOW,
        action=PolicyAction.ALLOW,
    ),
    Policy(
        id="message-user",
        name="Message User",
        description="Asking the user a question is always safe",
        tool_pattern=r"^message_ask_user$",
        risk_level=RiskLevel.LOW,
        action=PolicyAction.ALLOW,
    ),

    # === MEDIUM RISK: Allow + Log ===
    Policy(
        id="write-file",
        name="Write File",
        description="Creating or modifying files",
        tool_pattern=r"^(write_file|create_file|save_file|edit_file|append_file)$",
        risk_level=RiskLevel.MEDIUM,
        action=PolicyAction.ALLOW_AND_LOG,
    ),
    Policy(
        id="browser-interact",
        name="Browser Interaction",
        description="Clicking, typing, form submission in browser",
        tool_pattern=r"^(browser_click|browser_type|browser_select|browser_submit|browser_scroll|browser_press_key|browser_switch_tab|browser_close_tab|browser_wait)$",
        risk_level=RiskLevel.MEDIUM,
        action=PolicyAction.ALLOW_AND_LOG,
    ),
    Policy(
        id="mcp-call",
        name="MCP Tool Call",
        description="Calling external MCP tools",
        tool_pattern=r"^mcp_",
        risk_level=RiskLevel.MEDIUM,
        action=PolicyAction.ALLOW_AND_LOG,
    ),

    # === HIGH RISK: Allow + Log + Flag ===
    Policy(
        id="shell-exec",
        name="Shell Execution",
        description="Running shell commands can have system-wide effects",
        tool_pattern=r"^(shell_exec|execute_command|run_command|shell_run)$",
        risk_level=RiskLevel.HIGH,
        action=PolicyAction.ALLOW_AND_LOG,
    ),
    Policy(
        id="delete-file",
        name="Delete File",
        description="Deleting files is destructive and irreversible",
        tool_pattern=r"^(delete_file|remove_file)$",
        risk_level=RiskLevel.HIGH,
        action=PolicyAction.ALLOW_AND_LOG,
    ),

    # === CRITICAL: Block dangerous patterns ===
    Policy(
        id="block-rm-rf",
        name="Block rm -rf",
        description="Block recursive force delete commands",
        tool_pattern=r"^(shell_exec|execute_command|run_command|shell_run)$",
        arg_patterns={"command": r"rm\s+(-[a-zA-Z]*r[a-zA-Z]*f|--recursive\s+--force|-[a-zA-Z]*f[a-zA-Z]*r)\s+/"},
        risk_level=RiskLevel.CRITICAL,
        action=PolicyAction.BLOCK,
    ),
    Policy(
        id="block-env-leak",
        name="Block Environment Variable Leak",
        description="Block commands that could leak secrets",
        tool_pattern=r"^(shell_exec|execute_command|run_command|shell_run)$",
        arg_patterns={"command": r"(printenv|env\s*$|cat\s+.*\.env|echo\s+\$\{?(STRIPE|AWS|SECRET|API_KEY|PASSWORD))"},
        risk_level=RiskLevel.CRITICAL,
        action=PolicyAction.BLOCK,
    ),
    Policy(
        id="block-network-exfil",
        name="Block Data Exfiltration",
        description="Block commands that could send data to external servers",
        tool_pattern=r"^(shell_exec|execute_command|run_command|shell_run)$",
        arg_patterns={"command": r"(curl|wget|nc|netcat)\s+.*(-d|--data|--upload-file|<)"},
        risk_level=RiskLevel.CRITICAL,
        action=PolicyAction.BLOCK,
    ),
]


class PolicyEngine:
    """
    Evaluates tool calls against the policy set.
    Returns the most restrictive matching policy.
    """

    def __init__(self, policies: Optional[List[Policy]] = None):
        self.policies = policies or DEFAULT_POLICIES

    def evaluate(
        self,
        function_name: str,
        function_args: Dict[str, Any],
    ) -> tuple[Policy, PolicyAction]:
        """
        Evaluate a tool call against all policies.
        Returns (matched_policy, action).
        If no policy matches, defaults to ALLOW_AND_LOG (medium risk).
        """
        matched_policies: List[Policy] = []

        for policy in self.policies:
            if not policy.enabled:
                continue

            # Match tool name pattern
            if not re.match(policy.tool_pattern, function_name):
                continue

            # Match argument patterns (if any)
            if policy.arg_patterns:
                args_match = True
                for arg_name, arg_pattern in policy.arg_patterns.items():
                    arg_value = str(function_args.get(arg_name, ""))
                    if not re.search(arg_pattern, arg_value):
                        args_match = False
                        break
                if not args_match:
                    continue

            matched_policies.append(policy)

        if not matched_policies:
            # Default: unknown tools get medium risk + logging
            default_policy = Policy(
                id="default",
                name="Unknown Tool (Default)",
                description="No specific policy matched; applying default medium-risk logging",
                tool_pattern=".*",
                risk_level=RiskLevel.MEDIUM,
                action=PolicyAction.ALLOW_AND_LOG,
            )
            return default_policy, PolicyAction.ALLOW_AND_LOG

        # Return the most restrictive policy
        risk_priority = {
            RiskLevel.CRITICAL: 4,
            RiskLevel.HIGH: 3,
            RiskLevel.MEDIUM: 2,
            RiskLevel.LOW: 1,
        }
        matched_policies.sort(
            key=lambda p: risk_priority.get(p.risk_level, 0),
            reverse=True,
        )
        top = matched_policies[0]
        return top, top.action
