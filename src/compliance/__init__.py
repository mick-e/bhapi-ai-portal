"""Regulatory compliance module."""

# UK AADC public interface
from src.compliance.uk_aadc import (  # noqa: F401
    AADC_STANDARDS,
    apply_privacy_defaults,
    get_assessment_history,
    get_default_privacy_settings,
    get_latest_assessment,
    run_gap_analysis,
)
from src.compliance.uk_aadc_models import AadcAssessment, PrivacyDefault  # noqa: F401

# Australian Online Safety public interface
from src.compliance.australian import (  # noqa: F401
    check_au_age_requirement,
    check_esafety_sla,
    create_cyberbullying_case,
    close_cyberbullying_case,
    get_esafety_report,
)
from src.compliance.australian_models import (  # noqa: F401
    AgeVerificationRecord,
    CyberbullyingCase,
    ESafetyReport,
)
