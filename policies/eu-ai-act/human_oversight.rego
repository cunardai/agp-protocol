# eu_ai_act.human_oversight
# EU AI Act Article 14 — Human Oversight
#
# Verifies that mandatory human oversight measures are in place for high-risk AI
# systems. This package checks AGP task metadata for evidence of oversight
# configuration and raises violations when high-risk systems lack required controls.
#
# Reference: Regulation (EU) 2024/1689, Article 14

package eu_ai_act.human_oversight

import rego.v1

import data.eu_ai_act.risk_classification

# ── Art. 14(1): General obligation ────────────────────────────────────────────
# High-risk AI systems must be designed to allow effective human oversight.

# Art. 14(3)(a): Ability to understand system capabilities and limitations
missing_capability_disclosure(task) if {
    risk_classification.is_high_risk(task)
    not task.oversight.capability_disclosure_provided == true
}

# Art. 14(3)(b): Awareness of automation bias risk
missing_automation_bias_awareness(task) if {
    risk_classification.is_high_risk(task)
    not task.oversight.automation_bias_training_confirmed == true
}

# Art. 14(3)(c): Ability to interpret outputs correctly (explainability)
missing_interpretability(task) if {
    risk_classification.is_high_risk(task)
    not task.oversight.explainability_provided == true
}

# Art. 14(3)(d): Ability to disregard, override or reverse outputs
missing_override_mechanism(task) if {
    risk_classification.is_high_risk(task)
    not task.oversight.override_mechanism == true
}

# Art. 14(3)(e): Ability to intervene or interrupt via stop functionality
missing_stop_functionality(task) if {
    risk_classification.is_high_risk(task)
    not task.oversight.stop_functionality == true
}

# Art. 14(4): Appropriate human-AI ratio for monitoring
missing_human_monitor(task) if {
    risk_classification.is_high_risk(task)
    not task.oversight.human_monitor_assigned == true
}

# ── Critical/High-stakes: require explicit approval before execution ────────────

requires_prior_approval(task) if {
    risk_classification.is_high_risk(task)
    task.risk_tier in {"high", "critical"}
    not task.oversight.prior_human_approval == true
}

# ── Fully automated decisions affecting natural persons ────────────────────────
# Where AI makes decisions without any human involvement, stricter oversight required

is_fully_automated_decision(task) if {
    task.decision_mode == "fully_automated"
}

missing_automated_decision_safeguards(task) if {
    risk_classification.is_high_risk(task)
    is_fully_automated_decision(task)
    not task.oversight.right_to_explanation_provided == true
}

# ── Violations ─────────────────────────────────────────────────────────────────

violations contains rule if {
    missing_capability_disclosure(input.task)
    rule := "eu_ai_act.art14.3a.missing_capability_disclosure"
}

violations contains rule if {
    missing_automation_bias_awareness(input.task)
    rule := "eu_ai_act.art14.3b.missing_automation_bias_awareness"
}

violations contains rule if {
    missing_interpretability(input.task)
    rule := "eu_ai_act.art14.3c.missing_interpretability"
}

violations contains rule if {
    missing_override_mechanism(input.task)
    rule := "eu_ai_act.art14.3d.missing_override_mechanism"
}

violations contains rule if {
    missing_stop_functionality(input.task)
    rule := "eu_ai_act.art14.3e.missing_stop_functionality"
}

violations contains rule if {
    missing_human_monitor(input.task)
    rule := "eu_ai_act.art14.4.missing_human_monitor"
}

violations contains rule if {
    requires_prior_approval(input.task)
    rule := "eu_ai_act.art14.prior_approval_required"
}

violations contains rule if {
    missing_automated_decision_safeguards(input.task)
    rule := "eu_ai_act.art14.automated_decision_missing_right_to_explanation"
}

# ── Verdict ────────────────────────────────────────────────────────────────────

verdict := "require_approval" if count(violations) > 0

verdict := "allow" if count(violations) == 0

rationale := sprintf(
    "EU AI Act Article 14 human oversight violations: %v. High-risk AI systems must enable effective human oversight with override capability, stop functionality, explainability, and an assigned human monitor.",
    [violations]
) if count(violations) > 0
