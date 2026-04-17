"""
§9.1 Task State Machine — AGP Conformance Tests

Every valid and every invalid transition in the 14-state task machine.
"""
import pytest


# Valid transitions from the spec
VALID_TRANSITIONS = [
    ("CREATED",          "BOUND"),
    ("CREATED",          "REVOKED"),
    ("CREATED",          "FAILED"),
    ("BOUND",            "DELEGATED"),
    ("BOUND",            "SKILL_BOUND"),
    ("BOUND",            "COMMERCE_INIT"),
    ("BOUND",            "ANALYZING"),
    ("BOUND",            "REVOKED"),
    ("BOUND",            "FAILED"),
    ("DELEGATED",        "SKILL_BOUND"),
    ("DELEGATED",        "COMMERCE_INIT"),
    ("DELEGATED",        "ANALYZING"),
    ("DELEGATED",        "REVOKED"),
    ("DELEGATED",        "FAILED"),
    ("SKILL_BOUND",      "COMMERCE_INIT"),
    ("SKILL_BOUND",      "ANALYZING"),
    ("SKILL_BOUND",      "REVOKED"),
    ("SKILL_BOUND",      "FAILED"),
    ("COMMERCE_INIT",    "ANALYZING"),
    ("COMMERCE_INIT",    "REVOKED"),
    ("COMMERCE_INIT",    "FAILED"),
    ("ANALYZING",        "DECIDED"),
    ("ANALYZING",        "DENIED"),
    ("ANALYZING",        "REVOKED"),
    ("ANALYZING",        "FAILED"),
    ("DECIDED",          "POLICY_CHECKED"),
    ("DECIDED",          "DENIED"),
    ("DECIDED",          "REVOKED"),
    ("DECIDED",          "FAILED"),
    ("POLICY_CHECKED",   "APPROVAL_PENDING"),
    ("POLICY_CHECKED",   "EXECUTING"),
    ("POLICY_CHECKED",   "DENIED"),
    ("POLICY_CHECKED",   "QUARANTINED"),
    ("POLICY_CHECKED",   "REVOKED"),
    ("POLICY_CHECKED",   "FAILED"),
    ("APPROVAL_PENDING", "EXECUTING"),
    ("APPROVAL_PENDING", "DENIED"),
    ("APPROVAL_PENDING", "REVOKED"),
    ("APPROVAL_PENDING", "FAILED"),
    ("EXECUTING",        "COMPLETED"),
    ("EXECUTING",        "FAILED"),
    ("EXECUTING",        "REVOKED"),
]

# Terminal states — no further transitions allowed
TERMINAL_STATES = ["COMPLETED", "DENIED", "REVOKED", "QUARANTINED", "FAILED"]

# A sampling of clearly invalid transitions
INVALID_TRANSITIONS = [
    ("CREATED",        "DECIDED"),
    ("CREATED",        "EXECUTING"),
    ("CREATED",        "COMPLETED"),
    ("BOUND",          "COMPLETED"),
    ("BOUND",          "CREATED"),
    ("ANALYZING",      "CREATED"),
    ("DECIDED",        "CREATED"),
    ("DECIDED",        "ANALYZING"),
    ("EXECUTING",      "CREATED"),
    ("EXECUTING",      "BOUND"),
    ("EXECUTING",      "DECIDED"),
    ("POLICY_CHECKED", "CREATED"),
    ("POLICY_CHECKED", "BOUND"),
]


def _advance_to(c, task_id: str, target: str):
    """Advance a CREATED task to a specific state via the shortest valid path."""
    path = {
        "BOUND":            ["BOUND"],
        "DELEGATED":        ["BOUND", "DELEGATED"],
        "SKILL_BOUND":      ["BOUND", "SKILL_BOUND"],
        "COMMERCE_INIT":    ["BOUND", "COMMERCE_INIT"],
        "ANALYZING":        ["BOUND", "ANALYZING"],
        "DECIDED":          ["BOUND", "ANALYZING", "DECIDED"],
        "POLICY_CHECKED":   ["BOUND", "ANALYZING", "DECIDED", "POLICY_CHECKED"],
        "APPROVAL_PENDING": ["BOUND", "ANALYZING", "DECIDED", "POLICY_CHECKED", "APPROVAL_PENDING"],
        "EXECUTING":        ["BOUND", "ANALYZING", "DECIDED", "POLICY_CHECKED", "EXECUTING"],
    }
    for status in path.get(target, [target]):
        r = c.patch(f"/agp/tasks/{task_id}", {"status": status})
        assert r.status_code == 200, f"Could not advance to {status}: {r.text}"


class TestValidTransitions:
    """§9.1 — All transitions in the AGP state machine must be accepted."""

    @pytest.mark.parametrize("from_state,to_state", VALID_TRANSITIONS)
    def test_valid_transition(self, c, from_state, to_state):
        """§9.1 — Transition {from_state} → {to_state} must be accepted."""
        task = c.create_task()
        task_id = task["task_id"]
        if from_state != "CREATED":
            _advance_to(c, task_id, from_state)
        r = c.patch(f"/agp/tasks/{task_id}", {"status": to_state})
        assert r.status_code == 200, f"{from_state}→{to_state} rejected: {r.text}"
        assert r.json()["status"] == to_state


class TestInvalidTransitions:
    """§9.1 — Invalid transitions must be rejected."""

    @pytest.mark.parametrize("from_state,to_state", INVALID_TRANSITIONS)
    def test_invalid_transition(self, c, from_state, to_state):
        """§9.1 — Transition {from_state} → {to_state} must be rejected (422)."""
        task = c.create_task()
        task_id = task["task_id"]
        if from_state != "CREATED":
            _advance_to(c, task_id, from_state)
        r = c.patch(f"/agp/tasks/{task_id}", {"status": to_state})
        assert r.status_code == 422, (
            f"{from_state}→{to_state} should be rejected but got {r.status_code}: {r.text}"
        )

    @pytest.mark.parametrize("terminal", TERMINAL_STATES)
    def test_terminal_state_is_final(self, c, terminal):
        """§9.1 — Terminal states accept no further transitions."""
        task = c.create_task()
        task_id = task["task_id"]
        # Advance to the terminal state
        paths = {
            "COMPLETED":  ["BOUND", "ANALYZING", "DECIDED", "POLICY_CHECKED", "EXECUTING", "COMPLETED"],
            "DENIED":     ["BOUND", "ANALYZING", "DENIED"],
            "REVOKED":    ["REVOKED"],
            "QUARANTINED":["BOUND", "ANALYZING", "DECIDED", "POLICY_CHECKED", "QUARANTINED"],
            "FAILED":     ["FAILED"],
        }
        for s in paths[terminal]:
            c.patch(f"/agp/tasks/{task_id}", {"status": s})
        # Any further transition must fail
        r = c.patch(f"/agp/tasks/{task_id}", {"status": "CREATED"})
        assert r.status_code in (409, 422), (
            f"Terminal state {terminal} allowed transition: {r.status_code}"
        )

    def test_missing_status_field_rejected(self, c):
        """§9.1 — PATCH without status field returns 400."""
        task = c.create_task()
        r = c.patch(f"/agp/tasks/{task['task_id']}", {"note": "no status here"})
        assert r.status_code == 400

    def test_patch_nonexistent_task(self, c):
        """§9.1 — PATCH on unknown task_id returns 404."""
        r = c.patch("/agp/tasks/tsk_doesnotexist", {"status": "BOUND"})
        assert r.status_code == 404
