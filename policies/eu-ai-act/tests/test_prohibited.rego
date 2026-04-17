# Tests for eu_ai_act.prohibited (Article 5 prohibited practices)
# Run with: opa test policies/eu-ai-act/ -v

package eu_ai_act.prohibited_test

import rego.v1

import data.eu_ai_act.prohibited

# ── Art. 5(1)(a): Subliminal manipulation ─────────────────────────────────────

test_subliminal_manipulation_denied if {
    result := prohibited.verdict with input as {
        "task": {
            "operation_tags": ["subliminal_manipulation"],
            "principal_type": "commercial",
            "context": "general"
        }
    }
    result == "deny"
}

test_subconscious_influence_denied if {
    result := prohibited.verdict with input as {
        "task": {
            "operation_tags": ["subconscious_influence"],
            "principal_type": "commercial",
            "context": "general"
        }
    }
    result == "deny"
}

# ── Art. 5(1)(b): Vulnerability exploitation ─────────────────────────────────

test_exploit_vulnerability_denied if {
    result := prohibited.verdict with input as {
        "task": {
            "operation_tags": ["exploit_vulnerability"],
            "principal_type": "commercial",
            "context": "general"
        }
    }
    result == "deny"
}

test_exploit_age_disability_denied if {
    result := prohibited.verdict with input as {
        "task": {
            "operation_tags": ["exploit_age_disability"],
            "principal_type": "commercial",
            "context": "general"
        }
    }
    result == "deny"
}

# ── Art. 5(1)(c): Social scoring ─────────────────────────────────────────────

test_social_scoring_public_authority_denied if {
    result := prohibited.verdict with input as {
        "task": {
            "operation_tags": ["social_scoring"],
            "principal_type": "public_authority",
            "context": "general"
        }
    }
    result == "deny"
}

test_social_scoring_commercial_allowed if {
    # Social scoring by private entities is not prohibited under Art. 5(1)(c)
    violations := prohibited.violations with input as {
        "task": {
            "operation_tags": ["social_scoring"],
            "principal_type": "commercial",
            "context": "general"
        }
    }
    not "eu_ai_act.art5.1c.social_scoring" in violations
}

# ── Art. 5(1)(d): Real-time biometric identification ─────────────────────────

test_realtime_biometric_no_auth_denied if {
    result := prohibited.verdict with input as {
        "task": {
            "operation_tags": ["realtime_biometric_identification"],
            "principal_type": "public_authority",
            "context": "general",
            "law_enforcement_prior_authorisation": false
        }
    }
    result == "deny"
}

test_realtime_biometric_with_auth_allowed if {
    violations := prohibited.violations with input as {
        "task": {
            "operation_tags": ["realtime_biometric_identification"],
            "principal_type": "public_authority",
            "context": "general",
            "law_enforcement_prior_authorisation": true
        }
    }
    not "eu_ai_act.art5.1d.realtime_biometric_identification" in violations
}

# ── Art. 5(1)(e): Biometric categorisation ───────────────────────────────────

test_biometric_categorisation_race_denied if {
    result := prohibited.verdict with input as {
        "task": {
            "operation_tags": ["biometric_categorisation_race"],
            "principal_type": "commercial",
            "context": "general"
        }
    }
    result == "deny"
}

test_biometric_categorisation_political_denied if {
    result := prohibited.verdict with input as {
        "task": {
            "operation_tags": ["biometric_categorisation_political"],
            "principal_type": "commercial",
            "context": "general"
        }
    }
    result == "deny"
}

# ── Art. 5(1)(f): Emotion recognition ────────────────────────────────────────

test_emotion_recognition_workplace_denied if {
    result := prohibited.verdict with input as {
        "task": {
            "operation_tags": ["emotion_recognition"],
            "principal_type": "commercial",
            "context": "workplace"
        }
    }
    result == "deny"
}

test_emotion_recognition_education_denied if {
    result := prohibited.verdict with input as {
        "task": {
            "operation_tags": ["emotion_recognition"],
            "principal_type": "commercial",
            "context": "education_institution"
        }
    }
    result == "deny"
}

test_emotion_recognition_hospital_allowed if {
    # Emotion recognition in a hospital (medical context) is not prohibited
    violations := prohibited.violations with input as {
        "task": {
            "operation_tags": ["emotion_recognition"],
            "principal_type": "commercial",
            "context": "hospital"
        }
    }
    not "eu_ai_act.art5.1f.emotion_recognition" in violations
}

# ── Art. 5(1)(g): Predictive policing ────────────────────────────────────────

test_predictive_policing_individual_denied if {
    result := prohibited.verdict with input as {
        "task": {
            "operation_tags": ["predictive_policing_individual"],
            "principal_type": "public_authority",
            "context": "general"
        }
    }
    result == "deny"
}

test_criminal_risk_profiling_only_denied if {
    result := prohibited.verdict with input as {
        "task": {
            "operation_tags": ["criminal_risk_profiling_only"],
            "principal_type": "public_authority",
            "context": "general"
        }
    }
    result == "deny"
}

# ── Multiple violations ───────────────────────────────────────────────────────

test_multiple_violations_all_reported if {
    violations := prohibited.violations with input as {
        "task": {
            "operation_tags": ["subliminal_manipulation", "predictive_policing_individual"],
            "principal_type": "public_authority",
            "context": "general"
        }
    }
    "eu_ai_act.art5.1a.subliminal_manipulation" in violations
    "eu_ai_act.art5.1g.predictive_policing" in violations
}

# ── Clean task passes ─────────────────────────────────────────────────────────

test_clean_task_no_violations if {
    violations := prohibited.violations with input as {
        "task": {
            "operation_tags": ["data_analysis", "report_generation"],
            "principal_type": "commercial",
            "context": "general"
        }
    }
    count(violations) == 0
}

test_clean_task_no_verdict if {
    not prohibited.verdict with input as {
        "task": {
            "operation_tags": ["data_analysis"],
            "principal_type": "commercial",
            "context": "general"
        }
    }
}
