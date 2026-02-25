"""Report generators — PDF and CSV output for all report types."""

from src.reporting.generators.activity_report import ActivityReportGenerator
from src.reporting.generators.base import BaseGenerator
from src.reporting.generators.compliance_report import ComplianceReportGenerator
from src.reporting.generators.safety_report import SafetyReportGenerator
from src.reporting.generators.spend_report import SpendReportGenerator

GENERATORS: dict[str, type[BaseGenerator]] = {
    "risk": SafetyReportGenerator,
    "spend": SpendReportGenerator,
    "activity": ActivityReportGenerator,
    "compliance": ComplianceReportGenerator,
}

__all__ = [
    "GENERATORS",
    "BaseGenerator",
    "SafetyReportGenerator",
    "SpendReportGenerator",
    "ActivityReportGenerator",
    "ComplianceReportGenerator",
]
