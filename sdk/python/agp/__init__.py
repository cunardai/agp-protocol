"""
AGP Python SDK — Agent Governance Protocol

https://agp.dev
"""
from .admin import AdminClient
from .approvals import ApprovalsClient
from .client import AGPClient
from .content import ContentClient
from .detectors import DetectorsClient
from .ledger import LedgerClient
from .operator import OperatorClient
from .packs import PacksClient
from .principals import PrincipalsClient
from .exceptions import (
    AGPApprovalRequiredError,
    AGPBadRequestError,
    AGPConflictError,
    AGPConnectionError,
    AGPError,
    AGPNotFoundError,
    AGPPolicyDeniedError,
    AGPServerError,
    AGPTokenExpiredError,
    AGPTokenRevokedError,
    AGPUnprocessableError,
    AGPAuthNotConfiguredError,
    AGPForbiddenError,
    AGPImmutableError,
    AGPLedgerUnavailableError,
    AGPOrgReadOnlyError,
    AGPPrincipalBlockedError,
    AGPRateLimitedError,
    AGPTaintDetectedError,
    AGPUnauthorizedError,
)
from .models import (
    ActionEnvelope,
    ApprovalArtifact,
    AsyncOperation,
    AttestedContext,
    CapabilityToken,
    DecisionRecord,
    DelegationChain,
    EscalationNotice,
    EvidenceBundle,
    EventLedgerRecord,
    ExecutionReceipt,
    GovernanceAttestation,
    LiabilityBinding,
    PagedResult,
    PolicyDecision,
    PolicySet,
    RevocationNotice,
    SkillManifest,
    Task,
)
from .session import TaskSession

__version__ = "1.0.0"
__all__ = [
    "AGPClient",
    "TaskSession",
    # Exceptions
    "AGPError",
    "AGPNotFoundError",
    "AGPBadRequestError",
    "AGPConflictError",
    "AGPUnprocessableError",
    "AGPPolicyDeniedError",
    "AGPTokenRevokedError",
    "AGPTokenExpiredError",
    "AGPApprovalRequiredError",
    "AGPConnectionError",
    "AGPServerError",
    "AGPUnauthorizedError",
    "AGPForbiddenError",
    "AGPPrincipalBlockedError",
    "AGPImmutableError",
    "AGPTaintDetectedError",
    "AGPOrgReadOnlyError",
    "AGPRateLimitedError",
    "AGPLedgerUnavailableError",
    "AGPAuthNotConfiguredError",
    # AGP 1.0 clients
    "LedgerClient", "PrincipalsClient", "ContentClient", "AdminClient",
    "ApprovalsClient", "DetectorsClient", "PacksClient", "OperatorClient",
    # Models
    "Task",
    "LiabilityBinding",
    "CapabilityToken",
    "DelegationChain",
    "SkillManifest",
    "PolicySet",
    "RevocationNotice",
    "AttestedContext",
    "EvidenceBundle",
    "DecisionRecord",
    "PolicyDecision",
    "ApprovalArtifact",
    "EscalationNotice",
    "ActionEnvelope",
    "ExecutionReceipt",
    "EventLedgerRecord",
    "GovernanceAttestation",
    "AsyncOperation",
    "PagedResult",
]
