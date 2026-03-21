"""Content moderation pipeline module.

Public interface for cross-module communication.
Other modules should import only from this file.
"""

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
    ReportReason,
    ReportStatus,
    create_content_report,
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
    "create_content_report",
    "submit_for_moderation",
    "takedown_content",
    "update_report_status",
    "SocialRiskCategory",
    "SocialRiskResult",
    "ESafetyCategory",
    "ESafetyComplaint",
    "ESafetyPipeline",
    "TakedownStatus",
    "esafety_pipeline",
]
