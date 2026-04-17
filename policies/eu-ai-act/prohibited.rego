# eu_ai_act.prohibited
# EU AI Act Article 5 — Prohibited AI Practices
#
# These practices are banned outright regardless of risk tier or approval.
# A 'deny' verdict from this package cannot be overridden by human approval.
#
# Reference: Regulation (EU) 2024/1689, Article 5

package eu_ai_act.prohibited

import rego.v1

# ── Prohibited practice definitions ───────────────────────────────────────

# Art. 5(1)(a): Subliminal manipulation below conscious awareness
prohibited_subliminal(task) if {
    some tag in task.operation_tags
    tag in {
        "subliminal_manipulation",
        "subconscious_influence",
        "psychological_manipulation_covert"
    }
}

# Art. 5(1)(b): Exploiting vulnerabilities of specific groups
prohibited_vulnerability_exploitation(task) if {
    some tag in task.operation_tags
    tag in {
        "exploit_vulnerability",
        "target_vulnerable_group",
        "exploit_age_disability",
        "exploit_social_economic_situation"
    }
}

# Art. 5(1)(c): Social scoring by public authorities
prohibited_social_scoring(task) if {
    task.principal_type == "public_authority"
    some tag in task.operation_tags
    tag in {
        "social_scoring",
        "citizen_scoring",
        "social_credit"
    }
}

# Art. 5(1)(d): Real-time remote biometric identification in public spaces
# Exception: narrow law enforcement purposes with prior authorisation
prohibited_realtime_biometric(task) if {
    some tag in task.operation_tags
    tag in {
        "realtime_biometric_identification",
        "live_facial_recognition_public"
    }
    not task.law_enforcement_prior_authorisation == true
}

# Art. 5(1)(e): Biometric categorisation by sensitive attributes
prohibited_biometric_categorisation(task) if {
    some tag in task.operation_tags
    tag in {
        "biometric_categorisation_race",
        "biometric_categorisation_political",
        "biometric_categorisation_religion",
        "biometric_categorisation_sexual_orientation",
        "biometric_categorisation_trade_union"
    }
}

# Art. 5(1)(f): Emotion recognition in workplace or education
prohibited_emotion_recognition(task) if {
    some tag in task.operation_tags
    tag == "emotion_recognition"
    task.context in {"workplace", "education_institution"}
}

# Art. 5(1)(g): Individual criminal risk assessment from profiling alone
prohibited_predictive_policing(task) if {
    some tag in task.operation_tags
    tag in {
        "predictive_policing_individual",
        "criminal_risk_profiling_only"
    }
}

# ── Aggregate verdict ──────────────────────────────────────────────────────

violations contains rule if {
    prohibited_subliminal(input.task)
    rule := "eu_ai_act.art5.1a.subliminal_manipulation"
}

violations contains rule if {
    prohibited_vulnerability_exploitation(input.task)
    rule := "eu_ai_act.art5.1b.vulnerability_exploitation"
}

violations contains rule if {
    prohibited_social_scoring(input.task)
    rule := "eu_ai_act.art5.1c.social_scoring"
}

violations contains rule if {
    prohibited_realtime_biometric(input.task)
    rule := "eu_ai_act.art5.1d.realtime_biometric_identification"
}

violations contains rule if {
    prohibited_biometric_categorisation(input.task)
    rule := "eu_ai_act.art5.1e.biometric_categorisation"
}

violations contains rule if {
    prohibited_emotion_recognition(input.task)
    rule := "eu_ai_act.art5.1f.emotion_recognition"
}

violations contains rule if {
    prohibited_predictive_policing(input.task)
    rule := "eu_ai_act.art5.1g.predictive_policing"
}

# Final verdict for this package — deny overrides everything
verdict := "deny" if count(violations) > 0

rationale := sprintf(
    "EU AI Act Article 5 prohibited practice(s) detected. Violated rules: %v. These practices are banned outright under Regulation (EU) 2024/1689 and cannot be authorised by approval.",
    [violations]
) if count(violations) > 0
