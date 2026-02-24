"""Unit tests for LLM spend providers and threshold checker."""

from datetime import datetime, timezone

import pytest

from src.billing.providers.base import (
    BaseProvider,
    SpendEntry,
    AuthenticationError,
    RateLimitError,
)
from src.billing.providers.openai_client import OpenAIProvider
from src.billing.providers.anthropic_client import AnthropicProvider
from src.billing.providers.google_client import GoogleProvider
from src.billing.providers.microsoft_client import MicrosoftProvider
from src.billing.scheduler import get_provider, _PROVIDER_REGISTRY
from src.billing.threshold_checker import reset_fired_alerts


class TestSpendEntry:
    def test_default_values(self):
        entry = SpendEntry(amount=1.50)
        assert entry.amount == 1.50
        assert entry.currency == "USD"
        assert entry.period_start is None
        assert entry.token_count is None
        assert entry.raw_data == {}

    def test_full_entry(self):
        now = datetime.now(timezone.utc)
        entry = SpendEntry(
            amount=0.0035,
            currency="USD",
            period_start=now,
            period_end=now,
            token_count=1500,
            model="gpt-4o",
            raw_data={"test": True},
        )
        assert entry.token_count == 1500
        assert entry.model == "gpt-4o"


class TestBaseProvider:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            BaseProvider("test-key")


class TestProviderRegistry:
    def test_all_providers_registered(self):
        # Force registry init
        _PROVIDER_REGISTRY.clear()
        provider = get_provider("openai", "test-key")
        assert isinstance(provider, OpenAIProvider)

        provider = get_provider("anthropic", "test-key")
        assert isinstance(provider, AnthropicProvider)

        provider = get_provider("google", "test-key")
        assert isinstance(provider, GoogleProvider)

        provider = get_provider("microsoft", "test-key")
        assert isinstance(provider, MicrosoftProvider)

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            get_provider("unknown_llm", "test-key")


class TestOpenAIProvider:
    def test_provider_name(self):
        p = OpenAIProvider("sk-test")
        assert p.provider_name == "openai"

    def test_parse_costs_response(self):
        p = OpenAIProvider("sk-test")
        now = datetime.now(timezone.utc)
        data = {
            "data": [
                {
                    "results": [
                        {"amount": {"value": 150}, "line_item": "gpt-4o"},
                        {"amount": {"value": 50}, "line_item": "dall-e-3"},
                    ]
                }
            ]
        }
        entries = p._parse_costs_response(data, now, now)
        assert len(entries) == 2
        assert entries[0].amount == 1.50
        assert entries[0].model == "gpt-4o"
        assert entries[1].amount == 0.50

    def test_parse_empty_response(self):
        p = OpenAIProvider("sk-test")
        now = datetime.now(timezone.utc)
        entries = p._parse_costs_response({"data": []}, now, now)
        assert entries == []


class TestAnthropicProvider:
    def test_provider_name(self):
        p = AnthropicProvider("sk-ant-test")
        assert p.provider_name == "anthropic"

    def test_parse_usage_response(self):
        p = AnthropicProvider("sk-ant-test")
        now = datetime.now(timezone.utc)
        data = {
            "data": [
                {
                    "model": "claude-sonnet-4",
                    "input_tokens": 1000,
                    "output_tokens": 500,
                    "cost_usd": 0.0105,
                },
                {
                    "model": "claude-haiku-3.5",
                    "input_tokens": 2000,
                    "output_tokens": 1000,
                    "cost_usd": 0.0056,
                },
            ]
        }
        entries = p._parse_usage_response(data, now, now)
        assert len(entries) == 2
        assert entries[0].model == "claude-sonnet-4"
        assert entries[0].amount == 0.0105
        assert entries[0].token_count == 1500
        assert entries[1].token_count == 3000

    def test_estimate_cost_sonnet(self):
        cost = AnthropicProvider._estimate_cost(1_000_000, 500_000, "claude-sonnet-4")
        # 1M * 3.0/1M + 500K * 15.0/1M = 3.0 + 7.5 = 10.5
        assert cost == 10.5

    def test_estimate_cost_unknown_defaults_to_sonnet(self):
        cost = AnthropicProvider._estimate_cost(1_000_000, 0, "unknown-model")
        assert cost == 3.0  # 1M * 3.0/1M


class TestGoogleProvider:
    def test_provider_name(self):
        p = GoogleProvider("token-test")
        assert p.provider_name == "google"

    def test_parse_response(self):
        p = GoogleProvider("token-test")
        now = datetime.now(timezone.utc)
        data = {
            "costItems": [
                {
                    "cost": {"amount": 2.50, "currency": "USD"},
                    "sku": {"description": "Vertex AI Prediction"},
                },
                {
                    "cost": {"amount": 0.0, "currency": "USD"},
                    "sku": {"description": "Free tier"},
                },
            ]
        }
        entries = p._parse_response(data, now, now)
        assert len(entries) == 1
        assert entries[0].amount == 2.50


class TestMicrosoftProvider:
    def test_provider_name(self):
        p = MicrosoftProvider("token-test")
        assert p.provider_name == "microsoft"

    def test_parse_response(self):
        p = MicrosoftProvider("token-test")
        now = datetime.now(timezone.utc)
        data = {
            "properties": {
                "columns": [
                    {"name": "Cost"},
                    {"name": "MeterCategory"},
                ],
                "rows": [
                    [3.75, "Azure OpenAI"],
                    [1.25, "Cognitive Services"],
                    [0.0, "Free Services"],
                ],
            }
        }
        entries = p._parse_response(data, now, now)
        assert len(entries) == 2
        assert entries[0].amount == 3.75
        assert entries[0].model == "Azure OpenAI"


class TestThresholdChecker:
    def setup_method(self):
        reset_fired_alerts()
