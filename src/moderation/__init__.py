"""Content moderation pipeline module.

Public interface for cross-module communication.
Other modules should import only from this file.
"""

from src.moderation.anti_abuse import (
    INVITATION_LIMITS,
    AbuseType,
    check_content_manipulation,
    check_invitation_rate,
    detect_account_farming,
    detect_age_misrepresentation,
    detect_coordinated_harassment,
    detect_report_abuse,
    normalize_homoglyphs,
    normalize_leetspeak,
    record_abuse_signal,
)
from src.moderation.csam import CSAMCheckResult, CSAMDetector, NCMECReport, check_csam
from src.moderation.esafety import (
    ESafetyCategory,
    ESafetyComplaint,
    ESafetyPipeline,
    TakedownStatus,
)
from src.moderation.esafety import (
    pipeline as esafety_pipeline,
)
from src.moderation.image_pipeline import (
    ImageClassification,
    ImageModerationPipeline,
    ImageResult,
    classify_image,
)
from src.moderation.keyword_filter import FilterAction, FilterResult, classify_text
from src.moderation.service import (
    REPORT_REASON_LABELS,
    PostPublishResult,
    PostPublishSeverity,
    ReportReason,
    ReportStatus,
    create_appeal,
    create_content_report,
    decide_appeal,
    run_post_publish_moderation,
    submit_for_moderation,
    takedown_content,
    update_report_status,
)
from src.moderation.social_risk import (
    SocialRiskCategory,
    SocialRiskResult,
    classify_social_risk,
)
from src.moderation.video_pipeline import (
    VideoModerationPipeline,
    VideoResult,
    classify_video,
)

__all__ = [
    "CSAMCheckResult",
    "CSAMDetector",
    "FilterAction",
    "FilterResult",
    "ImageClassification",
    "ImageModerationPipeline",
    "ImageResult",
    "NCMECReport",
    "VideoModerationPipeline",
    "VideoResult",
    "check_csam",
    "classify_image",
    "classify_social_risk",
    "classify_text",
    "classify_video",
    "REPORT_REASON_LABELS",
    "ReportReason",
    "ReportStatus",
    "PostPublishResult",
    "PostPublishSeverity",
    "create_appeal",
    "create_content_report",
    "decide_appeal",
    "run_post_publish_moderation",
    "submit_for_moderation",
    "takedown_content",
    "update_report_status",
    "SocialRiskCategory",
    "SocialRiskResult",
    "AbuseType",
    "INVITATION_LIMITS",
    "check_content_manipulation",
    "check_invitation_rate",
    "detect_account_farming",
    "detect_age_misrepresentation",
    "detect_coordinated_harassment",
    "detect_report_abuse",
    "normalize_homoglyphs",
    "normalize_leetspeak",
    "record_abuse_signal",
    "ESafetyCategory",
    "ESafetyComplaint",
    "ESafetyPipeline",
    "TakedownStatus",
    "esafety_pipeline",
]
