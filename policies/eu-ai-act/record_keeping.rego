# eu_ai_act.record_keeping
# EU AI Act Article 12 — Record-Keeping (Logging)
#
# High-risk AI systems must have automatic logging capabilities enabling post-hoc
# audit of system operation. This package verifies that mandatory logging fields
# are present in the task and that AGP ledger configuration meets retention
# requirements.
#
# Reference: Regulation (EU) 2024/1689, Article 12

package eu_ai_act.record_keeping

import rego.v1

import data.eu_ai_act.risk_classification

# ── Art. 12(1): Automatic logging requirement ─────────────────────────────────

# High-risk systems must have logging enabled
missing_logging_enabled(task) if {
    risk_classification.is_high_risk(task)
    not task.record_keeping.logging_enabled == true
}

# ── Art. 12(2): Log content requirements ──────────────────────────────────────
# Logs must capture sufficient data to enable post-market monitoring and incident investigation.

missing_input_data_logging(task) if {
    risk_classification.is_high_risk(task)
    not task.record_keeping.input_data_logged == true
}

missing_output_logging(task) if {
    risk_classification.is_high_risk(task)
    not task.record_keeping.output_logged == true
}

missing_decision_basis_logging(task) if {
    risk_classification.is_high_risk(task)
    not task.record_keeping.decision_basis_logged == true
}

missing_human_oversight_events_logging(task) if {
    risk_classification.is_high_risk(task)
    not task.record_keeping.human_oversight_events_logged == true
}

missing_timestamps(task) if {
    risk_classification.is_high_risk(task)
    not task.record_keeping.timestamps_logged == true
}

# ── Art. 12(3): Retention period ──────────────────────────────────────────────
# Minimum log retention period varies by sector. General minimum: 6 months.
# Law enforcement: 3 years (Art. 12(3)(b)).

minimum_retention_months := 6
law_enforcement_retention_months := 36

required_retention(task) := law_enforcement_retention_months if {
    some tag in task.operation_tags
    tag in {
        "crime_analytics",
        "risk_assessment_criminal",
        "law_enforcement_detection",
        "profiling_law_enforcement"
    }
}

_is_law_enforcement(task) if {
    some tag in task.operation_tags
    tag in {
        "crime_analytics",
        "risk_assessment_criminal",
        "law_enforcement_detection",
        "profiling_law_enforcement"
    }
}

required_retention(task) := minimum_retention_months if {
    not _is_law_enforcement(task)
}

insufficient_retention(task) if {
    risk_classification.is_high_risk(task)
    task.record_keeping.retention_months < required_retention(task)
}

# ── Art. 12(4): Data integrity ────────────────────────────────────────────────
# Logs must be protected from tampering. AGP hash-chained ledger satisfies this.

missing_tamper_protection(task) if {
    risk_classification.is_high_risk(task)
    not task.record_keeping.tamper_protection_enabled == true
}

# ── AGP Ledger Binding ────────────────────────────────────────────────────────
# If the task has an AGP ledger ref, that satisfies tamper protection (hash-chain)
# and timestamps requirements automatically.

has_agp_ledger(task) if {
    task.record_keeping.agp_ledger_bound == true
}

# Ledger binding satisfies tamper protection and timestamps
effective_missing_tamper_protection(task) if {
    missing_tamper_protection(task)
    not has_agp_ledger(task)
}

effective_missing_timestamps(task) if {
    missing_timestamps(task)
    not has_agp_ledger(task)
}

# ── Violations ─────────────────────────────────────────────────────────────────

violations contains rule if {
    missing_logging_enabled(input.task)
    rule := "eu_ai_act.art12.1.logging_not_enabled"
}

violations contains rule if {
    missing_input_data_logging(input.task)
    rule := "eu_ai_act.art12.2.input_data_not_logged"
}

violations contains rule if {
    missing_output_logging(input.task)
    rule := "eu_ai_act.art12.2.output_not_logged"
}

violations contains rule if {
    missing_decision_basis_logging(input.task)
    rule := "eu_ai_act.art12.2.decision_basis_not_logged"
}

violations contains rule if {
    missing_human_oversight_events_logging(input.task)
    rule := "eu_ai_act.art12.2.human_oversight_events_not_logged"
}

violations contains rule if {
    effective_missing_timestamps(input.task)
    rule := "eu_ai_act.art12.2.timestamps_not_logged"
}

violations contains rule if {
    insufficient_retention(input.task)
    rule := sprintf(
        "eu_ai_act.art12.3.insufficient_retention_period (required: %v months)",
        [required_retention(input.task)]
    )
}

violations contains rule if {
    effective_missing_tamper_protection(input.task)
    rule := "eu_ai_act.art12.4.missing_tamper_protection"
}

# ── Obligations ────────────────────────────────────────────────────────────────

obligations contains "eu_ai_act.art12.bind_agp_ledger" if {
    risk_classification.is_high_risk(input.task)
    not has_agp_ledger(input.task)
}

# ── Verdict ────────────────────────────────────────────────────────────────────

verdict := "deny" if {
    missing_logging_enabled(input.task)
    risk_classification.is_high_risk(input.task)
}

verdict := "require_approval" if {
    not missing_logging_enabled(input.task)
    count(violations) > 0
}

verdict := "allow" if count(violations) == 0

rationale := sprintf(
    "EU AI Act Article 12 record-keeping violations: %v. High-risk AI systems require automatic, tamper-protected logging of inputs, outputs, decision basis, and human oversight events with a minimum %v-month retention period.",
    [violations, required_retention(input.task)]
) if count(violations) > 0
