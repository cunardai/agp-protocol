# eu_ai_act.risk_classification
# EU AI Act Articles 6 + Annex III — High-Risk AI System Classification
#
# Determines whether an AI system is classified as high-risk under the EU AI Act
# and which high-risk category applies. High-risk classification triggers mandatory
# obligations under Articles 9-17.
#
# Reference: Regulation (EU) 2024/1689, Article 6 and Annex III

package eu_ai_act.risk_classification

import rego.v1

# ── Annex III High-Risk Categories ────────────────────────────────────────────

# Annex III §1: Biometric identification and categorisation of natural persons
annex3_biometric(task) if {
    some tag in task.operation_tags
    tag in {
        "biometric_identification",
        "biometric_verification",
        "biometric_categorisation",
        "emotion_recognition_realtime"
    }
}

# Annex III §2: Critical infrastructure management
annex3_critical_infrastructure(task) if {
    some tag in task.operation_tags
    tag in {
        "critical_infrastructure_management",
        "traffic_management",
        "utility_grid_management",
        "water_supply_management",
        "digital_infrastructure_management"
    }
}

# Annex III §3: Education and vocational training
annex3_education(task) if {
    some tag in task.operation_tags
    tag in {
        "education_assessment",
        "student_evaluation",
        "admission_decision",
        "exam_monitoring",
        "learning_outcome_assessment"
    }
}

# Annex III §4: Employment, workers management, access to self-employment
annex3_employment(task) if {
    some tag in task.operation_tags
    tag in {
        "recruitment_screening",
        "cv_screening",
        "job_candidate_ranking",
        "employment_decision",
        "employee_monitoring",
        "performance_evaluation",
        "promotion_decision",
        "termination_decision",
        "work_allocation"
    }
}

# Annex III §5: Access to and enjoyment of essential private services and public services and benefits
annex3_essential_services(task) if {
    some tag in task.operation_tags
    tag in {
        "credit_scoring",
        "loan_decision",
        "insurance_risk_assessment",
        "social_benefit_eligibility",
        "public_service_eligibility",
        "healthcare_access_decision",
        "emergency_dispatch"
    }
}

# Annex III §6: Law enforcement
annex3_law_enforcement(task) if {
    some tag in task.operation_tags
    tag in {
        "lie_detection",
        "evidence_reliability_assessment",
        "crime_analytics",
        "risk_assessment_criminal",
        "profiling_law_enforcement",
        "crime_prediction"
    }
}

# Annex III §7: Migration, asylum and border control management
annex3_migration(task) if {
    some tag in task.operation_tags
    tag in {
        "asylum_assessment",
        "visa_decision",
        "border_control_risk_assessment",
        "migration_risk_profiling",
        "travel_document_verification"
    }
}

# Annex III §8: Administration of justice and democratic processes
annex3_justice(task) if {
    some tag in task.operation_tags
    tag in {
        "judicial_decision_support",
        "legal_outcome_prediction",
        "case_outcome_assessment",
        "electoral_process",
        "political_campaign_targeting"
    }
}

# ── Safety Component Check (Article 6(1)) ─────────────────────────────────────
# Systems that are safety components of products covered by EU harmonisation legislation

is_safety_component(task) if {
    task.is_safety_component == true
}

# ── High-Risk Determination ────────────────────────────────────────────────────

annex3_category(task) := category if {
    annex3_biometric(task)
    category := "annex3_1_biometric"
}

annex3_category(task) := category if {
    not annex3_biometric(task)
    annex3_critical_infrastructure(task)
    category := "annex3_2_critical_infrastructure"
}

annex3_category(task) := category if {
    not annex3_biometric(task)
    not annex3_critical_infrastructure(task)
    annex3_education(task)
    category := "annex3_3_education"
}

annex3_category(task) := category if {
    not annex3_biometric(task)
    not annex3_critical_infrastructure(task)
    not annex3_education(task)
    annex3_employment(task)
    category := "annex3_4_employment"
}

annex3_category(task) := category if {
    not annex3_biometric(task)
    not annex3_critical_infrastructure(task)
    not annex3_education(task)
    not annex3_employment(task)
    annex3_essential_services(task)
    category := "annex3_5_essential_services"
}

annex3_category(task) := category if {
    not annex3_biometric(task)
    not annex3_critical_infrastructure(task)
    not annex3_education(task)
    not annex3_employment(task)
    not annex3_essential_services(task)
    annex3_law_enforcement(task)
    category := "annex3_6_law_enforcement"
}

annex3_category(task) := category if {
    not annex3_biometric(task)
    not annex3_critical_infrastructure(task)
    not annex3_education(task)
    not annex3_employment(task)
    not annex3_essential_services(task)
    not annex3_law_enforcement(task)
    annex3_migration(task)
    category := "annex3_7_migration"
}

annex3_category(task) := category if {
    not annex3_biometric(task)
    not annex3_critical_infrastructure(task)
    not annex3_education(task)
    not annex3_employment(task)
    not annex3_essential_services(task)
    not annex3_law_enforcement(task)
    not annex3_migration(task)
    annex3_justice(task)
    category := "annex3_8_justice"
}

is_high_risk(task) if annex3_category(task)
is_high_risk(task) if is_safety_component(task)

# ── GPAI Model Detection ───────────────────────────────────────────────────────
# General Purpose AI models (Articles 51-56) have separate obligations

is_gpai(task) if {
    task.system_type == "gpai_model"
}

is_gpai_systemic_risk(task) if {
    is_gpai(task)
    task.gpai_training_flops >= 1e25  # Art. 51(2) threshold
}

# ── Obligations triggered by high-risk classification ─────────────────────────

obligations contains "eu_ai_act.art9.risk_management_system" if is_high_risk(input.task)
obligations contains "eu_ai_act.art10.data_governance" if is_high_risk(input.task)
obligations contains "eu_ai_act.art11.technical_documentation" if is_high_risk(input.task)
obligations contains "eu_ai_act.art12.record_keeping" if is_high_risk(input.task)
obligations contains "eu_ai_act.art13.transparency" if is_high_risk(input.task)
obligations contains "eu_ai_act.art14.human_oversight" if is_high_risk(input.task)
obligations contains "eu_ai_act.art15.accuracy_robustness" if is_high_risk(input.task)
obligations contains "eu_ai_act.art16.qms_registration" if is_high_risk(input.task)
obligations contains "eu_ai_act.art51_56.gpai_obligations" if is_gpai(input.task)
obligations contains "eu_ai_act.art55.systemic_risk_obligations" if is_gpai_systemic_risk(input.task)

# ── Violations: non-compliance with declared risk tier ─────────────────────────

violations contains rule if {
    is_high_risk(input.task)
    input.task.risk_tier != "high"
    input.task.risk_tier != "critical"
    rule := "eu_ai_act.art6.risk_tier_mismatch"
}

# ── Output ─────────────────────────────────────────────────────────────────────

risk_classification := result if {
    is_high_risk(input.task)
    result := {
        "is_high_risk": true,
        "is_safety_component": is_safety_component(input.task),
        "annex3_category": annex3_category(input.task),
        "is_gpai": is_gpai(input.task),
        "is_gpai_systemic_risk": is_gpai_systemic_risk(input.task),
    }
}

risk_classification := result if {
    not is_high_risk(input.task)
    result := {
        "is_high_risk": false,
        "is_safety_component": false,
        "is_gpai": input.task.system_type == "gpai_model",
        "is_gpai_systemic_risk": false,
    }
}

verdict := "require_approval" if {
    count(violations) > 0
    count(obligations) > 0
}

verdict := "allow" if {
    count(violations) == 0
}

rationale := sprintf(
    "EU AI Act risk classification: high-risk system detected (category: %v). Mandatory obligations: %v. Violations: %v",
    [annex3_category(input.task), obligations, violations]
) if is_high_risk(input.task)
