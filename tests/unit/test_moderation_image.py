"""Unit tests for image moderation pipeline."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.moderation.image_pipeline import (
    DEFAULT_THRESHOLDS,
    ImageClassification,
    ImageModerationPipeline,
    ImageResult,
    classify_image,
    pipeline,
)


@pytest.fixture
def img_pipeline() -> ImageModerationPipeline:
    """Fresh pipeline instance for each test."""
    return ImageModerationPipeline()


@pytest.fixture
def configured_pipeline() -> ImageModerationPipeline:
    """Pipeline with Hive API key configured."""
    p = ImageModerationPipeline()
    p.configure(hive_api_key="test-hive-key")
    return p


def _hive_response(classes: list[dict]) -> dict:
    """Build a Hive API response with given classes."""
    return {
        "status": [
            {
                "response": {
                    "output": [
                        {"classes": classes}
                    ]
                }
            }
        ]
    }


# --- Classification enum ---

class TestImageClassification:
    def test_values(self):
        assert ImageClassification.SAFE == "safe"
        assert ImageClassification.UNSAFE == "unsafe"
        assert ImageClassification.NEEDS_REVIEW == "needs_review"
        assert ImageClassification.ERROR == "error"

    def test_all_values_exist(self):
        values = {e.value for e in ImageClassification}
        assert values == {"safe", "unsafe", "needs_review", "error"}


# --- ImageResult dataclass ---

class TestImageResult:
    def test_defaults(self):
        r = ImageResult(classification=ImageClassification.SAFE, confidence=0.9)
        assert r.categories == {}
        assert r.provider == "none"

    def test_with_categories(self):
        cats = {"nsfw": 0.1, "violence": 0.2}
        r = ImageResult(
            classification=ImageClassification.SAFE,
            confidence=0.8,
            categories=cats,
            provider="hive",
        )
        assert r.categories == cats
        assert r.provider == "hive"


# --- Pipeline configuration ---

class TestPipelineConfig:
    def test_default_thresholds(self, img_pipeline):
        assert img_pipeline._thresholds == DEFAULT_THRESHOLDS

    def test_configure_hive_key(self, img_pipeline):
        img_pipeline.configure(hive_api_key="key1")
        assert img_pipeline._hive_api_key == "key1"

    def test_configure_sensity_key(self, img_pipeline):
        img_pipeline.configure(sensity_api_key="key2")
        assert img_pipeline._sensity_api_key == "key2"

    def test_configure_cf_secret(self, img_pipeline):
        img_pipeline.configure(cf_webhook_secret="secret")
        assert img_pipeline._cf_webhook_secret == "secret"

    def test_configure_partial(self, img_pipeline):
        img_pipeline.configure(hive_api_key="h1")
        img_pipeline.configure(sensity_api_key="s1")
        assert img_pipeline._hive_api_key == "h1"
        assert img_pipeline._sensity_api_key == "s1"

    def test_set_thresholds(self, img_pipeline):
        img_pipeline.set_thresholds({"nsfw": 0.5})
        assert img_pipeline._thresholds["nsfw"] == 0.5
        # Other defaults remain
        assert img_pipeline._thresholds["violence"] == 0.7


# --- Threshold adjustment ---

class TestThresholdAdjustment:
    def test_young_tier_lowers_thresholds(self, img_pipeline):
        adjusted = img_pipeline._adjust_thresholds("young")
        assert adjusted["nsfw"] == pytest.approx(0.48)  # 0.8 * 0.6
        assert adjusted["self_harm"] == pytest.approx(0.36)  # 0.6 * 0.6

    def test_preteen_tier(self, img_pipeline):
        adjusted = img_pipeline._adjust_thresholds("preteen")
        assert adjusted["nsfw"] == pytest.approx(0.64)  # 0.8 * 0.8

    def test_teen_tier_no_change(self, img_pipeline):
        adjusted = img_pipeline._adjust_thresholds("teen")
        assert adjusted == img_pipeline._thresholds

    def test_none_tier_no_change(self, img_pipeline):
        adjusted = img_pipeline._adjust_thresholds(None)
        assert adjusted == img_pipeline._thresholds

    def test_unknown_tier_no_change(self, img_pipeline):
        adjusted = img_pipeline._adjust_thresholds("adult")
        assert adjusted == img_pipeline._thresholds


# --- classify_image (no API key) ---

class TestClassifyNoApiKey:
    @pytest.mark.asyncio
    async def test_no_api_key_returns_needs_review(self, img_pipeline):
        result = await img_pipeline.classify_image("https://example.com/img.jpg")
        assert result.classification == ImageClassification.NEEDS_REVIEW
        assert result.confidence == 0.0
        assert result.provider == "none"

    @pytest.mark.asyncio
    async def test_empty_url_returns_error(self, img_pipeline):
        result = await img_pipeline.classify_image("")
        assert result.classification == ImageClassification.ERROR

    @pytest.mark.asyncio
    async def test_whitespace_url_returns_error(self, img_pipeline):
        result = await img_pipeline.classify_image("   ")
        assert result.classification == ImageClassification.ERROR

    @pytest.mark.asyncio
    async def test_invalid_scheme_returns_error(self, img_pipeline):
        result = await img_pipeline.classify_image("ftp://example.com/img.jpg")
        assert result.classification == ImageClassification.ERROR

    @pytest.mark.asyncio
    async def test_relative_url_returns_error(self, img_pipeline):
        result = await img_pipeline.classify_image("/images/test.jpg")
        assert result.classification == ImageClassification.ERROR


# --- classify_image (with mocked Hive API) ---

class TestClassifyWithHive:
    @pytest.mark.asyncio
    async def test_safe_image(self, configured_pipeline):
        hive_resp = _hive_response([
            {"class": "nsfw", "score": 0.05},
            {"class": "violence", "score": 0.01},
        ])
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = hive_resp
        mock_response.raise_for_status = MagicMock()

        with patch("src.moderation.image_pipeline.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            result = await configured_pipeline.classify_image("https://example.com/safe.jpg")

        assert result.classification == ImageClassification.SAFE
        assert result.provider == "hive"
        assert result.categories["nsfw"] == 0.05

    @pytest.mark.asyncio
    async def test_unsafe_image_nsfw(self, configured_pipeline):
        hive_resp = _hive_response([
            {"class": "nsfw", "score": 0.95},
            {"class": "violence", "score": 0.1},
        ])
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = hive_resp
        mock_response.raise_for_status = MagicMock()

        with patch("src.moderation.image_pipeline.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            result = await configured_pipeline.classify_image("https://example.com/bad.jpg")

        assert result.classification == ImageClassification.UNSAFE
        assert result.confidence == 0.95

    @pytest.mark.asyncio
    async def test_unsafe_violence(self, configured_pipeline):
        hive_resp = _hive_response([
            {"class": "nsfw", "score": 0.1},
            {"class": "violence", "score": 0.85},
        ])
        mock_response = MagicMock()
        mock_response.json.return_value = hive_resp
        mock_response.raise_for_status = MagicMock()

        with patch("src.moderation.image_pipeline.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            result = await configured_pipeline.classify_image("https://example.com/v.jpg")

        assert result.classification == ImageClassification.UNSAFE
        assert result.confidence == 0.85

    @pytest.mark.asyncio
    async def test_borderline_needs_review(self, configured_pipeline):
        """Score within 10% of threshold triggers NEEDS_REVIEW."""
        hive_resp = _hive_response([
            {"class": "nsfw", "score": 0.75},  # > 0.8*0.9=0.72 but < 0.8
        ])
        mock_response = MagicMock()
        mock_response.json.return_value = hive_resp
        mock_response.raise_for_status = MagicMock()

        with patch("src.moderation.image_pipeline.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            result = await configured_pipeline.classify_image("https://example.com/border.jpg")

        assert result.classification == ImageClassification.NEEDS_REVIEW

    @pytest.mark.asyncio
    async def test_young_tier_lower_threshold(self, configured_pipeline):
        """Young age tier uses 0.6 multiplier, so nsfw threshold becomes 0.48."""
        hive_resp = _hive_response([
            {"class": "nsfw", "score": 0.5},  # > 0.48 threshold for young
        ])
        mock_response = MagicMock()
        mock_response.json.return_value = hive_resp
        mock_response.raise_for_status = MagicMock()

        with patch("src.moderation.image_pipeline.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            result = await configured_pipeline.classify_image(
                "https://example.com/img.jpg", age_tier="young"
            )

        assert result.classification == ImageClassification.UNSAFE

    @pytest.mark.asyncio
    async def test_api_timeout_returns_needs_review(self, configured_pipeline):
        import httpx as httpx_mod

        with patch("src.moderation.image_pipeline.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.side_effect = httpx_mod.TimeoutException("timeout")
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            result = await configured_pipeline.classify_image("https://example.com/img.jpg")

        assert result.classification == ImageClassification.NEEDS_REVIEW
        assert result.provider == "hive"

    @pytest.mark.asyncio
    async def test_api_http_error_returns_needs_review(self, configured_pipeline):
        import httpx as httpx_mod

        mock_resp = MagicMock()
        mock_resp.status_code = 500

        with patch("src.moderation.image_pipeline.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.side_effect = httpx_mod.HTTPStatusError(
                "server error", request=MagicMock(), response=mock_resp
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            result = await configured_pipeline.classify_image("https://example.com/img.jpg")

        assert result.classification == ImageClassification.NEEDS_REVIEW

    @pytest.mark.asyncio
    async def test_generic_exception_returns_needs_review(self, configured_pipeline):
        with patch("src.moderation.image_pipeline.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.side_effect = RuntimeError("unexpected")
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            result = await configured_pipeline.classify_image("https://example.com/img.jpg")

        assert result.classification == ImageClassification.NEEDS_REVIEW


# --- Hive response parsing ---

class TestParseHiveResponse:
    def test_empty_status_list(self, configured_pipeline):
        data = {"status": []}
        result = configured_pipeline._parse_hive_response(data, DEFAULT_THRESHOLDS)
        assert result.classification == ImageClassification.NEEDS_REVIEW

    def test_no_status_key(self, configured_pipeline):
        data = {}
        result = configured_pipeline._parse_hive_response(data, DEFAULT_THRESHOLDS)
        assert result.classification == ImageClassification.NEEDS_REVIEW

    def test_empty_output(self, configured_pipeline):
        data = {"status": [{"response": {"output": []}}]}
        result = configured_pipeline._parse_hive_response(data, DEFAULT_THRESHOLDS)
        assert result.classification == ImageClassification.SAFE
        assert result.confidence == 1.0

    def test_multiple_classes_worst_wins(self, configured_pipeline):
        data = _hive_response([
            {"class": "nsfw", "score": 0.05},
            {"class": "violence", "score": 0.05},
            {"class": "self_harm", "score": 0.95},  # Exceeds 0.6 threshold
        ])
        result = configured_pipeline._parse_hive_response(data, DEFAULT_THRESHOLDS)
        assert result.classification == ImageClassification.UNSAFE
        assert result.confidence == 0.95

    def test_class_with_empty_name_skipped(self, configured_pipeline):
        data = _hive_response([
            {"class": "", "score": 0.99},
            {"class": "nsfw", "score": 0.01},
        ])
        result = configured_pipeline._parse_hive_response(data, DEFAULT_THRESHOLDS)
        # Empty class name is stored but not matched to any threshold
        assert result.classification == ImageClassification.SAFE


# --- CF webhook handling ---

class TestCFWebhook:
    @pytest.mark.asyncio
    async def test_valid_payload(self, img_pipeline):
        payload = {
            "id": "abc123",
            "variants": ["https://img.cf.com/abc123/public"],
        }
        result = await img_pipeline.handle_cf_images_webhook(payload)
        assert result["status"] == "processed"
        assert result["image_id"] == "abc123"

    @pytest.mark.asyncio
    async def test_missing_id(self, img_pipeline):
        payload = {"variants": ["https://img.cf.com/abc/public"]}
        result = await img_pipeline.handle_cf_images_webhook(payload)
        assert result["status"] == "ignored"
        assert "missing" in result["reason"]

    @pytest.mark.asyncio
    async def test_missing_variants(self, img_pipeline):
        payload = {"id": "abc123"}
        result = await img_pipeline.handle_cf_images_webhook(payload)
        assert result["status"] == "ignored"

    @pytest.mark.asyncio
    async def test_empty_variants(self, img_pipeline):
        payload = {"id": "abc123", "variants": []}
        result = await img_pipeline.handle_cf_images_webhook(payload)
        assert result["status"] == "ignored"

    @pytest.mark.asyncio
    async def test_invalid_payload_type(self, img_pipeline):
        result = await img_pipeline.handle_cf_images_webhook("not a dict")
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_non_string_variant(self, img_pipeline):
        payload = {"id": "abc123", "variants": [123]}
        result = await img_pipeline.handle_cf_images_webhook(payload)
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_meta_age_tier(self, img_pipeline):
        """Age tier from meta is passed through."""
        payload = {
            "id": "abc123",
            "variants": ["https://img.cf.com/abc123/public"],
            "meta": {"age_tier": "young"},
        }
        result = await img_pipeline.handle_cf_images_webhook(payload)
        assert result["status"] == "processed"

    @pytest.mark.asyncio
    async def test_invalid_meta_type(self, img_pipeline):
        """Non-dict meta is handled gracefully."""
        payload = {
            "id": "abc123",
            "variants": ["https://img.cf.com/abc123/public"],
            "meta": "invalid",
        }
        result = await img_pipeline.handle_cf_images_webhook(payload)
        assert result["status"] == "processed"

    @pytest.mark.asyncio
    async def test_variants_not_list(self, img_pipeline):
        payload = {"id": "abc123", "variants": "not-a-list"}
        result = await img_pipeline.handle_cf_images_webhook(payload)
        assert result["status"] == "ignored"


# --- Webhook signature verification ---

class TestWebhookSignature:
    def test_no_secret_accepts_all(self, img_pipeline):
        assert img_pipeline.verify_cf_signature(b"body", "any-sig") is True

    def test_valid_signature(self, img_pipeline):
        import hashlib
        import hmac as hmac_mod

        img_pipeline.configure(cf_webhook_secret="test-secret")
        body = b'{"id": "123"}'
        sig = hmac_mod.new(b"test-secret", body, hashlib.sha256).hexdigest()
        assert img_pipeline.verify_cf_signature(body, sig) is True

    def test_invalid_signature(self, img_pipeline):
        img_pipeline.configure(cf_webhook_secret="test-secret")
        assert img_pipeline.verify_cf_signature(b"body", "wrong-sig") is False


# --- Module-level classify_image function ---

class TestModuleLevelFunction:
    @pytest.mark.asyncio
    async def test_classify_image_delegates_to_pipeline(self):
        with patch.object(pipeline, "classify_image", new_callable=AsyncMock) as mock:
            mock.return_value = ImageResult(
                classification=ImageClassification.SAFE,
                confidence=0.9,
            )
            result = await classify_image("https://example.com/img.jpg", age_tier="teen")
            mock.assert_called_once_with("https://example.com/img.jpg", "teen")
            assert result.classification == ImageClassification.SAFE
