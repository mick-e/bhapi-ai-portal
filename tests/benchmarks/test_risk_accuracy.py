"""CI guard tests for AI monitoring accuracy benchmarks.

These tests verify that:
1. The labeled test corpus exists and meets minimum size requirements.
2. The keyword classifier achieves a baseline accuracy threshold on the corpus.
3. The benchmark runner produces valid metrics and reports.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

CORPUS = Path("tests/benchmarks/data/risk_test_corpus.json")


def test_corpus_exists_and_meets_minimum_size():
    """The risk test corpus must exist with at least 70 labeled examples."""
    assert CORPUS.exists(), f"Corpus not found at {CORPUS}"
    data = json.loads(CORPUS.read_text(encoding="utf-8"))
    assert len(data) >= 70, f"Corpus has {len(data)} examples, need 70+"


def test_corpus_covers_all_categories():
    """Every taxonomy category must have at least 5 examples."""
    from src.risk.taxonomy import ALL_CATEGORIES

    data = json.loads(CORPUS.read_text(encoding="utf-8"))
    category_counts: dict[str, int] = {}
    for entry in data:
        cat = entry["true_category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1

    for cat in ALL_CATEGORIES:
        count = category_counts.get(cat, 0)
        assert count >= 5, f"Category {cat} has only {count} examples, need 5+"


def test_corpus_has_safe_examples():
    """The corpus must include SAFE examples to test false-positive rates."""
    data = json.loads(CORPUS.read_text(encoding="utf-8"))
    safe_count = sum(1 for e in data if e["true_category"] == "SAFE")
    assert safe_count >= 5, f"Only {safe_count} SAFE examples, need 5+"


def test_corpus_entries_have_required_fields():
    """Every corpus entry must have id, content, true_category fields."""
    data = json.loads(CORPUS.read_text(encoding="utf-8"))
    for entry in data:
        assert "id" in entry, f"Entry missing 'id': {entry}"
        assert "content" in entry, f"Entry {entry.get('id')} missing 'content'"
        assert "true_category" in entry, f"Entry {entry.get('id')} missing 'true_category'"


@pytest.mark.asyncio
async def test_keyword_classifier_accuracy():
    """Verify keyword classifier meets baseline accuracy on the labeled corpus.

    The current keyword classifier is expected to achieve at least 60%
    overall accuracy.  Categories not covered by keyword patterns
    (e.g. PII_EXPOSURE, SPEND_ANOMALY, EXCESSIVE_USAGE, UNKNOWN_PLATFORM,
    RADICALISATION) will naturally score lower, pulling down the aggregate.
    As AI-based classifiers are added the threshold should be raised.
    """
    from src.risk.benchmarks import _result_matches_category
    from src.risk.classifier import classify_content

    data = json.loads(CORPUS.read_text(encoding="utf-8"))

    correct = 0
    total = 0
    for example in data:
        result = await classify_content(example["content"])
        true_cat = example["true_category"]
        if _result_matches_category(result, true_cat):
            correct += 1
        total += 1

    accuracy = correct / total if total else 0
    assert accuracy >= 0.60, f"Accuracy {accuracy:.2%} below 60% threshold"


@pytest.mark.asyncio
async def test_benchmark_runner_produces_valid_metrics():
    """Run the full benchmark pipeline and verify the output structure."""
    from src.risk.benchmarks import compute_metrics, load_corpus, run_benchmark

    corpus = load_corpus(CORPUS)
    raw = await run_benchmark(corpus)

    assert "results" in raw
    assert "elapsed_seconds" in raw
    assert len(raw["results"]) == len(corpus)

    metrics = compute_metrics(raw)
    assert "accuracy" in metrics
    assert "per_category" in metrics
    assert 0.0 <= metrics["accuracy"] <= 1.0
    assert metrics["total"] == len(corpus)


@pytest.mark.asyncio
async def test_benchmark_report_generation():
    """The Markdown report must contain expected sections."""
    from src.risk.benchmarks import (
        compute_metrics,
        generate_report,
        load_corpus,
        run_benchmark,
    )

    corpus = load_corpus(CORPUS)
    raw = await run_benchmark(corpus)
    metrics = compute_metrics(raw)
    report = generate_report(metrics)

    assert "# AI Monitoring Accuracy Benchmark Report" in report
    assert "Per-Category Metrics" in report
    assert "| Category |" in report
    assert "Precision" in report
    assert "Recall" in report
