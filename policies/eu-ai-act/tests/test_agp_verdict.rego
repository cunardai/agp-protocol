# Integration tests for eu_ai_act.agp_verdict (aggregator)
# Verifies verdict precedence and full PolicyDecision output shape.
# Run with: opa test policies/eu-ai-act/ -v

package eu_ai_act.agp_verdict_test

import rego.v1

import data.eu_ai_act.agp_verdict

# ── Helper: clean low-risk task ────────────────────────────────────────────────

clean_task := {
    "operation_tags": ["data_analysis", "report_generation"],
    "principal_type": "commercial",
    "context": "general",
    "risk_tier": "low",
    "interaction_mode": "batch",
    "system_type": "task_specific",
    "decision_mode": "human_in_the_loop",
    "is_safety_component": false,
    "record_keeping": {
        "logging_enabled": true,
        "input_data_logged": true,
        "output_logged": true,
        "decision_basis_logged": true,
        "human_oversight_events_logged": true,
        "timestamps_logged": true,
        "retention_months": 6,
        "tamper_protection_enabled": true,
        "agp_ledger_bound": true
    },
    "transparency": {
        "ai_identity_disclosed": true,
        "system_card_provided": true,
        "intended_purpose_disclosed": true,
        "known_limitations_disclosed": true
    },
    "oversight": {}
}

# ── Art. 5 prohibited: deny takes absolute precedence ─────────────────────────

test_prohibited_yields_deny if {
    result := agp_verdict.verdict with input as {
        "task": {
            "operation_tags": ["subliminal_manipulation"],
            "principal_type": "commercial",
            "context": "general",
            "risk_tier": "low",
            "system_type": "task_specific",
            "is_safety_component": false,
            "record_keeping": {"logging_enabled": true},
            "transparency": {},
            "oversight": {}
        }
    }
    result == "deny"
}

test_prohibited_rationale_mentions_article5 if {
    result := agp_verdict.rationale with input as {
        "task": {
            "operation_tags": ["subliminal_manipulation"],
            "principal_type": "commercial",
            "context": "general",
            "risk_tier": "low",
            "system_type": "task_specific",
            "is_safety_component": false,
            "record_keeping": {"logging_enabled": true},
            "transparency": {},
            "oversight": {}
        }
    }
    contains(result, "Article 5")
}

# ── Clean task: allow ─────────────────────────────────────────────────────────

test_clean_task_allowed if {
    result := agp_verdict.verdict with input as {"task": clean_task}
    result == "allow"
}

test_clean_task_no_violations if {
    violations := agp_verdict.all_violations with input as {"task": clean_task}
    count(violations) == 0
}

test_clean_task_policy_decision_shape if {
    pd := agp_verdict.policy_decision with input as {"task": clean_task}
    pd.verdict == "allow"
    pd.matched_rules == set()
    pd.obligations == set()
    pd.rationale != ""
}

# ── High-risk without oversight: require_approval ─────────────────────────────

test_high_risk_missing_oversight_requires_approval if {
    result := agp_verdict.verdict with input as {
        "task": {
            "operation_tags": ["recruitment_screening"],
            "principal_type": "commercial",
            "context": "general",
            "risk_tier": "high",
            "system_type": "task_specific",
            "is_safety_component": false,
            "decision_mode": "fully_automated",
            "record_keeping": {
                "logging_enabled": true,
                "input_data_logged": true,
                "output_logged": true,
                "decision_basis_logged": true,
                "human_oversight_events_logged": true,
                "agp_ledger_bound": true,
                "retention_months": 6
            },
            "transparency": {
                "system_card_provided": true,
                "intended_purpose_disclosed": true,
                "known_limitations_disclosed": true
            },
            "oversight": {
                "logging_enabled": true
                # Missing: override_mechanism, stop_functionality, human_monitor_assigned, etc.
            }
        }
    }
    result == "require_approval"
}

# ── Logging disabled on high-risk: deny ───────────────────────────────────────

test_high_risk_no_logging_denied if {
    result := agp_verdict.verdict with input as {
        "task": {
            "operation_tags": ["loan_decision"],
            "principal_type": "commercial",
            "context": "general",
            "risk_tier": "high",
            "system_type": "task_specific",
            "is_safety_component": false,
            "decision_mode": "human_in_the_loop",
            "record_keeping": {
                "logging_enabled": false
            },
            "transparency": {
                "system_card_provided": true,
                "intended_purpose_disclosed": true,
                "known_limitations_disclosed": true
            },
            "oversight": {
                "capability_disclosure_provided": true,
                "automation_bias_training_confirmed": true,
                "explainability_provided": true,
                "override_mechanism": true,
                "stop_functionality": true,
                "human_monitor_assigned": true,
                "prior_human_approval": true
            }
        }
    }
    result == "deny"
}

# ── Conversational AI without disclosure: require_approval ────────────────────

test_chatbot_without_disclosure_requires_approval if {
    result := agp_verdict.verdict with input as {
        "task": {
            "operation_tags": ["customer_query_response"],
            "principal_type": "commercial",
            "context": "general",
            "risk_tier": "low",
            "system_type": "task_specific",
            "is_safety_component": false,
            "interaction_mode": "chatbot",
            "decision_mode": "human_in_the_loop",
            "record_keeping": {
                "logging_enabled": true,
                "input_data_logged": true,
                "output_logged": true,
                "decision_basis_logged": true,
                "human_oversight_events_logged": true,
                "agp_ledger_bound": true,
                "retention_months": 6
            },
            "transparency": {
                "ai_identity_disclosed": false  # Missing disclosure
            },
            "oversight": {}
        }
    }
    result == "require_approval"
}

# ── Verdict with obligations ──────────────────────────────────────────────────

test_high_risk_without_ledger_has_obligation if {
    obligations := agp_verdict.all_obligations with input as {
        "task": {
            "operation_tags": ["job_candidate_ranking"],
            "principal_type": "commercial",
            "context": "general",
            "risk_tier": "high",
            "system_type": "task_specific",
            "is_safety_component": false,
            "decision_mode": "human_in_the_loop",
            "record_keeping": {
                "logging_enabled": true,
                "input_data_logged": true,
                "output_logged": true,
                "decision_basis_logged": true,
                "human_oversight_events_logged": true,
                "agp_ledger_bound": false,  # Not yet bound
                "tamper_protection_enabled": true,
                "retention_months": 6
            },
            "transparency": {
                "system_card_provided": true,
                "intended_purpose_disclosed": true,
                "known_limitations_disclosed": true
            },
            "oversight": {
                "capability_disclosure_provided": true,
                "automation_bias_training_confirmed": true,
                "explainability_provided": true,
                "override_mechanism": true,
                "stop_functionality": true,
                "human_monitor_assigned": true,
                "prior_human_approval": true
            }
        }
    }
    "eu_ai_act.art12.bind_agp_ledger" in obligations
}
