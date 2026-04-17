"""FERPA compliance module — educational record management and audit logging.

Public interface for cross-module communication.
Other modules should import only from this file, never from internal submodules.
"""

from src.ferpa.models import (
    AccessLog,
    AnnualNotification,
    DataSharingAgreement,
    EducationalRecord,
)
from src.ferpa.schemas import (
    AccessLogCreate,
    AccessLogResponse,
    AnnualNotificationCreate,
    AnnualNotificationResponse,
    DataSharingAgreementCreate,
    DataSharingAgreementResponse,
    EducationalRecordCreate,
    EducationalRecordResponse,
)
from src.ferpa.service import (
    create_data_sharing_agreement,
    create_educational_record,
    list_access_logs,
    list_data_sharing_agreements,
    list_educational_records,
    log_access,
    send_annual_notification,
)

__all__ = [
    "AccessLog",
    "AccessLogCreate",
    "AccessLogResponse",
    "AnnualNotification",
    "AnnualNotificationCreate",
    "AnnualNotificationResponse",
    "DataSharingAgreement",
    "DataSharingAgreementCreate",
    "DataSharingAgreementResponse",
    "EducationalRecord",
    "EducationalRecordCreate",
    "EducationalRecordResponse",
    "create_data_sharing_agreement",
    "create_educational_record",
    "list_access_logs",
    "list_data_sharing_agreements",
    "list_educational_records",
    "log_access",
    "send_annual_notification",
]
