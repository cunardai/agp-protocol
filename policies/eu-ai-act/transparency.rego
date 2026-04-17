# eu_ai_act.transparency
# EU AI Act Article 50 — Transparency Obligations for Certain AI Systems
#
# Applies to AI systems that interact with natural persons, generate synthetic
# content, or make outputs that could be mistaken for human-generated content.
# These obligations apply regardless of risk tier.
#
# Reference: Regulation (EU) 2024/1689, Article 50

package eu_ai_act.transparency

import rego.v1

import data.eu_ai_act.risk_classification

# ── Art. 50(1): Disclosure when interacting with natural persons ───────────────
# AI systems designed to interact with natural persons must disclose they are AI.

interacts_with_natural_persons(task) if {
    task.interaction_mode in {
        "conversational_ai",
        "chatbot",
        "virtual_assistant",
        "customer_service_bot",
        "voice_assistant"
    }
}

missing_ai_disclosure(task) if {
    interacts_with_natural_persons(task)
    not task.transparency.ai_identity_disclosed == true
}

# Exception: lawfully authorised detection/investigation by law enforcement
law_enforcement_detection_exception(task) if {
    task.principal_type == "public_authority"
    task.law_enforcement_prior_authorisation == true
    some tag in task.operation_tags
    tag == "law_enforcement_detection"
}

# ── Art. 50(2): Emotion recognition or biometric categorisation disclosure ─────

uses_emotion_recognition(task) if {
    some tag in task.operation_tags
    tag == "emotion_recognition"
}

uses_biometric_categorisation(task) if {
    some tag in task.operation_tags
    tag in {
        "biometric_categorisation_race",
        "biometric_categorisation_political",
        "biometric_categorisation_religion",
        "biometric_categorisation_sexual_orientation",
        "biometric_categorisation_trade_union",
        "biometric_categorisation"
    }
}

missing_emotion_recognition_disclosure(task) if {
    uses_emotion_recognition(task)
    not task.transparency.emotion_recognition_disclosed == true
}

missing_biometric_categorisation_disclosure(task) if {
    uses_biometric_categorisation(task)
    not task.transparency.biometric_categorisation_disclosed == true
}

# ── Art. 50(3): Synthetic content marking (deepfakes etc.) ───────────────────
# AI-generated images, audio, video must be marked as artificially generated.

generates_synthetic_content(task) if {
    some tag in task.operation_tags
    tag in {
        "synthetic_image_generation",
        "synthetic_audio_generation",
        "synthetic_video_generation",
        "deepfake_generation",
        "voice_cloning",
        "face_swap"
    }
}

# Exceptions: authorised law enforcement use or artistic/satirical purposes with disclosure
artistic_or_satire_exception(task) if {
    task.content_purpose in {"artistic", "satire", "parody"}
    task.transparency.artistic_purpose_disclosed == true
}

missing_synthetic_content_marking(task) if {
    generates_synthetic_content(task)
    not artistic_or_satire_exception(task)
    not task.transparency.synthetic_content_marked == true
}

# ── Art. 50(4): Disclosure for AI-generated text on matters of public interest ─

generates_public_interest_text(task) if {
    some tag in task.operation_tags
    tag in {
        "news_generation",
        "political_content_generation",
        "public_affairs_content"
    }
}

missing_ai_generated_text_disclosure(task) if {
    generates_public_interest_text(task)
    not task.transparency.ai_generated_text_disclosed == true
}

# ── High-risk transparency obligations (from Art. 13) ─────────────────────────
# High-risk systems must provide information enabling meaningful understanding.

missing_high_risk_system_card(task) if {
    risk_classification.is_high_risk(task)
    not task.transparency.system_card_provided == true
}

missing_intended_purpose_disclosure(task) if {
    risk_classification.is_high_risk(task)
    not task.transparency.intended_purpose_disclosed == true
}

missing_limitation_disclosure(task) if {
    risk_classification.is_high_risk(task)
    not task.transparency.known_limitations_disclosed == true
}

# ── Violations ─────────────────────────────────────────────────────────────────

violations contains rule if {
    missing_ai_disclosure(input.task)
    not law_enforcement_detection_exception(input.task)
    rule := "eu_ai_act.art50.1.missing_ai_identity_disclosure"
}

violations contains rule if {
    missing_emotion_recognition_disclosure(input.task)
    rule := "eu_ai_act.art50.2.missing_emotion_recognition_disclosure"
}

violations contains rule if {
    missing_biometric_categorisation_disclosure(input.task)
    rule := "eu_ai_act.art50.2.missing_biometric_categorisation_disclosure"
}

violations contains rule if {
    missing_synthetic_content_marking(input.task)
    rule := "eu_ai_act.art50.3.missing_synthetic_content_marking"
}

violations contains rule if {
    missing_ai_generated_text_disclosure(input.task)
    rule := "eu_ai_act.art50.4.missing_ai_text_disclosure"
}

violations contains rule if {
    missing_high_risk_system_card(input.task)
    rule := "eu_ai_act.art13.missing_system_card"
}

violations contains rule if {
    missing_intended_purpose_disclosure(input.task)
    rule := "eu_ai_act.art13.missing_intended_purpose"
}

violations contains rule if {
    missing_limitation_disclosure(input.task)
    rule := "eu_ai_act.art13.missing_limitation_disclosure"
}

# ── Verdict ────────────────────────────────────────────────────────────────────

verdict := "require_approval" if count(violations) > 0

verdict := "allow" if count(violations) == 0

rationale := sprintf(
    "EU AI Act Article 50 transparency violations: %v. Affected parties must be informed when interacting with AI systems, consuming AI-generated content, or subject to AI-based categorisation.",
    [violations]
) if count(violations) > 0
