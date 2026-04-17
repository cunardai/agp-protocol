# eu_ai_act.agp_verdict
# EU AI Act — AGP PolicyDecision Aggregator
#
# Combines verdicts from all eu_ai_act sub-packages into a single AGP
# PolicyDecision. Verdict precedence (highest wins):
#   deny > require_approval > require_stronger_auth > quarantine > allow
#
# The output of this package maps directly to the AGP PolicyDecision schema:
#   verdict, matched_rules, obligations, rationale
#
# Reference: Regulation (EU) 2024/1689 (EU AI Act)
# AGP Schema: https://agp.dev/schema/objects/policy-decision.json

package eu_ai_act.agp_verdict

import rego.v1

import data.eu_ai_act.prohibited
import data.eu_ai_act.risk_classification
import data.eu_ai_act.human_oversight
import data.eu_ai_act.transparency
import data.eu_ai_act.record_keeping

# ── Collect all violations across packages ────────────────────────────────────

all_violations contains v if some v in prohibited.violations
all_violations contains v if some v in risk_classification.violations
all_violations contains v if some v in human_oversight.violations
all_violations contains v if some v in transparency.violations
all_violations contains v if some v in record_keeping.violations

# ── Collect all obligations across packages ───────────────────────────────────

all_obligations contains o if some o in risk_classification.obligations
all_obligations contains o if some o in record_keeping.obligations

# ── Verdict precedence ────────────────────────────────────────────────────────
#
# "deny" from prohibited.rego is absolute — EU AI Act Art. 5 cannot be overridden.
# Other packages may emit require_approval; those are aggregated upward.

is_prohibited if prohibited.verdict == "deny"

is_denied if {
    is_prohibited
}

is_denied if {
    human_oversight.verdict == "deny"
}

is_denied if {
    record_keeping.verdict == "deny"
}

is_require_approval if {
    not is_denied
    some pkg_verdict in {
        risk_classification.verdict,
        human_oversight.verdict,
        transparency.verdict,
        record_keeping.verdict,
    }
    pkg_verdict == "require_approval"
}

# ── Final aggregated verdict ──────────────────────────────────────────────────

verdict := "deny" if is_denied

verdict := "require_approval" if {
    not is_denied
    is_require_approval
}

verdict := "allow" if {
    not is_denied
    not is_require_approval
}

# ── Rationale assembly ────────────────────────────────────────────────────────

rationale := msg if {
    is_prohibited
    msg := sprintf(
        "[EU AI Act] ABSOLUTE DENIAL — Article 5 prohibited practice(s). These cannot be overridden by human approval or any other mechanism. Violated rules: %v",
        [prohibited.violations]
    )
}

rationale := msg if {
    not is_prohibited
    is_denied
    msg := sprintf(
        "[EU AI Act] DENIED — Mandatory compliance failures that block execution: %v. All violations must be remediated before this task may proceed.",
        [all_violations]
    )
}

rationale := msg if {
    not is_denied
    is_require_approval
    msg := sprintf(
        "[EU AI Act] REQUIRES APPROVAL — High-risk AI system or transparency/oversight violations detected. Violations: %v. Pending obligations: %v.",
        [all_violations, all_obligations]
    )
}

rationale := msg if {
    verdict == "allow"
    count(all_violations) == 0
    count(all_obligations) == 0
    msg := "[EU AI Act] ALLOWED — No prohibited practices, no high-risk classification triggers, all transparency and record-keeping requirements satisfied."
}

rationale := msg if {
    verdict == "allow"
    count(all_violations) == 0
    count(all_obligations) > 0
    msg := sprintf(
        "[EU AI Act] ALLOWED with obligations — System is permitted to execute but must fulfil: %v",
        [all_obligations]
    )
}

# ── AGP PolicyDecision output fields ─────────────────────────────────────────
# These map 1:1 to the PolicyDecision JSON schema fields that the AGP server
# populates when recording the result of OPA evaluation.

policy_decision := {
    "verdict":       verdict,
    "matched_rules": all_violations,
    "obligations":   all_obligations,
    "rationale":     rationale,
    "risk_classification": risk_classification.risk_classification,
}
