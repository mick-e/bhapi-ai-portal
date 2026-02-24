"""Unit tests for report generators."""

import json
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.reporting.generators import GENERATORS
from src.reporting.generators.base import BaseGenerator
from src.reporting.generators.safety_report import SafetyReportGenerator
from src.reporting.generators.spend_report import SpendReportGenerator
from src.reporting.generators.activity_report import ActivityReportGenerator
from src.reporting.generators.compliance_report import ComplianceReportGenerator


class TestGeneratorRegistry:
    def test_all_generators_registered(self):
        assert "risk" in GENERATORS
        assert "spend" in GENERATORS
        assert "activity" in GENERATORS
        assert "compliance" in GENERATORS

    def test_risk_maps_to_safety(self):
        assert GENERATORS["risk"] is SafetyReportGenerator

    def test_spend_maps_to_spend(self):
        assert GENERATORS["spend"] is SpendReportGenerator

    def test_activity_maps_to_activity(self):
        assert GENERATORS["activity"] is ActivityReportGenerator

    def test_compliance_maps_to_compliance(self):
        assert GENERATORS["compliance"] is ComplianceReportGenerator


class TestBaseGenerator:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            BaseGenerator(None, None)

    def test_safety_report_type(self):
        assert SafetyReportGenerator.report_type == "risk"
        assert SafetyReportGenerator.title == "Safety Report"

    def test_spend_report_type(self):
        assert SpendReportGenerator.report_type == "spend"
        assert SpendReportGenerator.title == "Spend Report"

    def test_activity_report_type(self):
        assert ActivityReportGenerator.report_type == "activity"
        assert ActivityReportGenerator.title == "Activity Report"

    def test_compliance_report_type(self):
        assert ComplianceReportGenerator.report_type == "compliance"
        assert ComplianceReportGenerator.title == "Compliance & Safeguarding Report"


class TestSafetyReportColumns:
    def test_columns(self):
        gen = SafetyReportGenerator.__new__(SafetyReportGenerator)
        cols = gen.get_columns()
        assert cols == ["Date", "Member", "Category", "Severity", "Confidence", "Acknowledged"]

    def test_row_to_values(self):
        gen = SafetyReportGenerator.__new__(SafetyReportGenerator)
        row = {
            "date": "2024-01-15 10:30",
            "member_name": "Alice",
            "category": "self_harm",
            "severity": "critical",
            "confidence": 0.95,
            "acknowledged": "No",
        }
        values = gen.row_to_values(row)
        assert values == ["2024-01-15 10:30", "Alice", "self_harm", "critical", "0.95", "No"]


class TestSpendReportColumns:
    def test_columns(self):
        gen = SpendReportGenerator.__new__(SpendReportGenerator)
        cols = gen.get_columns()
        assert cols == ["Date", "Provider", "Model", "Member", "Amount", "Tokens"]

    def test_row_to_values(self):
        gen = SpendReportGenerator.__new__(SpendReportGenerator)
        row = {
            "date": "2024-01-15",
            "provider": "openai",
            "model": "gpt-4o",
            "member_name": "Bob",
            "amount": "$1.50",
            "tokens": "1500",
        }
        values = gen.row_to_values(row)
        assert values == ["2024-01-15", "openai", "gpt-4o", "Bob", "$1.50", "1500"]


class TestActivityReportColumns:
    def test_columns(self):
        gen = ActivityReportGenerator.__new__(ActivityReportGenerator)
        cols = gen.get_columns()
        assert cols == ["Date/Time", "Member", "Platform", "Event Type", "Source"]

    def test_row_to_values(self):
        gen = ActivityReportGenerator.__new__(ActivityReportGenerator)
        row = {
            "timestamp": "2024-01-15 10:30",
            "member_name": "Charlie",
            "platform": "chatgpt",
            "event_type": "prompt",
            "source": "extension",
        }
        values = gen.row_to_values(row)
        assert values == ["2024-01-15 10:30", "Charlie", "chatgpt", "prompt", "extension"]


class TestComplianceReportColumns:
    def test_columns(self):
        gen = ComplianceReportGenerator.__new__(ComplianceReportGenerator)
        cols = gen.get_columns()
        assert cols == ["Date", "Record Type", "Detail", "Member/Resource", "Status"]

    def test_row_to_values(self):
        gen = ComplianceReportGenerator.__new__(ComplianceReportGenerator)
        row = {
            "date": "2024-01-15 10:30",
            "type": "Consent",
            "detail": "monitoring",
            "member_name": "Dave",
            "status": "Active",
        }
        values = gen.row_to_values(row)
        assert values == ["2024-01-15 10:30", "Consent", "monitoring", "Dave", "Active"]
