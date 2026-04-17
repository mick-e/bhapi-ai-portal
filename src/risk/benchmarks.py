"""AI monitoring accuracy benchmark runner.

Loads a labeled JSON corpus, classifies each example using
``classify_content``, and computes precision / recall / F1 per risk
category.  Results are written as a Markdown report.

Usage::

    python -m src.risk.benchmarks [corpus_path] [output_path]

If *corpus_path* is omitted the default test corpus is used.
If *output_path* is omitted the report goes to stdout.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

import structlog

from src.risk.classifier import ClassificationResult, classify_content
from src.risk.taxonomy import ALL_CATEGORIES, RISK_CATEGORIES

logger = structlog.get_logger()

DEFAULT_CORPUS = Path("tests/benchmarks/data/risk_test_corpus.json")

# ---------------------------------------------------------------------------
# Mapping helpers
# ---------------------------------------------------------------------------
# The keyword classifier returns generic bucket names (e.g. "safety",
# "harmful_content") rather than taxonomy category names.  For benchmark
# scoring we need a mapping from the classifier's returned categories +
# severity level back to the canonical taxonomy categories.

# Severity level -> set of taxonomy categories that the classifier may indicate.
# The keyword classifier returns generic bucket names, not taxonomy names,
# so we map by severity tier.  If the classifier fires at a given severity,
# any taxonomy category in that tier (or higher) is considered a plausible
# match.
_SEVERITY_TO_TAXONOMY: dict[str, set[str]] = {
    "critical": {
        "SELF_HARM", "VIOLENCE", "RADICALISATION", "CSAM_ADJACENT",
    },
    "high": {
        "ADULT_CONTENT", "SCAM_MANIPULATION", "PII_EXPOSURE",
        "DEEPFAKE_CONTENT", "BULLYING_HARASSMENT",
    },
    "medium": {
        "ACADEMIC_DISHONESTY", "BULLYING_HARASSMENT", "SPEND_ANOMALY",
        "EMOTIONAL_DEPENDENCY", "ADULT_CONTENT",
    },
}

# Categories that the keyword classifier has NO patterns for at all.
# These are expected to be missed entirely and rely on the AI classifier.
KEYWORD_BLIND_CATEGORIES: frozenset[str] = frozenset({
    "RADICALISATION",
    "PII_EXPOSURE",
    "SPEND_ANOMALY",
    "EXCESSIVE_USAGE",
    "UNKNOWN_PLATFORM",
})


def _result_matches_category(
    result: ClassificationResult,
    true_category: str,
) -> bool:
    """Return True if *result* is consistent with *true_category*.

    For ``SAFE`` entries the classifier should return no categories or low
    severity.  For taxonomy categories we check whether the classifier's
    returned severity + buckets can plausibly map to the true category.
    """
    if true_category == "SAFE":
        return not result.categories or result.severity == "low"

    # Direct hit — the category name appears verbatim (e.g. DEEPFAKE_CONTENT,
    # EMOTIONAL_DEPENDENCY)
    if true_category in result.categories:
        return True

    # Map by severity: if the classifier flagged at the right severity tier,
    # accept it as a match for any taxonomy category in that tier.
    mapped = _SEVERITY_TO_TAXONOMY.get(result.severity, set())
    return true_category in mapped


# ---------------------------------------------------------------------------
# Corpus loading
# ---------------------------------------------------------------------------

def load_corpus(path: Path) -> list[dict]:
    """Load and validate the JSON corpus file."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Corpus must be a JSON array")
    for i, entry in enumerate(data):
        for field in ("id", "content", "true_category"):
            if field not in entry:
                raise ValueError(f"Entry {i} missing required field '{field}'")
    return data


# ---------------------------------------------------------------------------
# Benchmark execution
# ---------------------------------------------------------------------------

async def run_benchmark(corpus: list[dict]) -> dict:
    """Run ``classify_content`` on every corpus entry and return raw results.

    Returns a dict with ``results`` (per-example) and ``elapsed_seconds``.
    """
    results: list[dict] = []
    t0 = time.monotonic()

    for entry in corpus:
        result = await classify_content(entry["content"])
        matched = _result_matches_category(result, entry["true_category"])
        results.append({
            "id": entry["id"],
            "true_category": entry["true_category"],
            "true_severity": entry.get("true_severity", "unknown"),
            "predicted_severity": result.severity,
            "predicted_categories": result.categories,
            "confidence": result.confidence,
            "source": result.source,
            "matched": matched,
        })

    elapsed = time.monotonic() - t0
    return {"results": results, "elapsed_seconds": round(elapsed, 3)}


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def compute_metrics(raw: dict) -> dict:
    """Compute per-category precision, recall, F1 and overall accuracy."""
    results = raw["results"]

    # True positives, false positives, false negatives per category
    tp: dict[str, int] = defaultdict(int)
    fp: dict[str, int] = defaultdict(int)
    fn: dict[str, int] = defaultdict(int)

    correct = 0
    total = len(results)

    for r in results:
        cat = r["true_category"]
        if r["matched"]:
            correct += 1
            tp[cat] += 1
        else:
            fn[cat] += 1
            # Count as false positive for whatever the classifier predicted
            pred_cats = r["predicted_categories"]
            for pc in pred_cats:
                fp[pc] += 1

    # All categories that appear in the corpus (including SAFE)
    categories = sorted({r["true_category"] for r in results})

    per_category: dict[str, dict] = {}
    for cat in categories:
        t = tp[cat]
        f_p = fp.get(cat, 0)
        f_n = fn[cat]
        precision = t / (t + f_p) if (t + f_p) else 0.0
        recall = t / (t + f_n) if (t + f_n) else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall)
            else 0.0
        )
        per_category[cat] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "tp": t,
            "fp": f_p,
            "fn": f_n,
        }

    accuracy = correct / total if total else 0.0
    return {
        "accuracy": round(accuracy, 4),
        "total": total,
        "correct": correct,
        "per_category": per_category,
        "elapsed_seconds": raw["elapsed_seconds"],
    }


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_report(metrics: dict) -> str:
    """Generate a Markdown benchmark report from computed metrics."""
    lines: list[str] = []
    lines.append("# AI Monitoring Accuracy Benchmark Report\n")
    lines.append(f"**Corpus size:** {metrics['total']} examples  ")
    lines.append(f"**Overall accuracy:** {metrics['accuracy']:.2%}  ")
    lines.append(f"**Correct:** {metrics['correct']} / {metrics['total']}  ")
    lines.append(f"**Elapsed:** {metrics['elapsed_seconds']:.3f}s\n")

    lines.append("## Per-Category Metrics\n")
    lines.append(
        "| Category | Precision | Recall | F1 | TP | FP | FN |"
    )
    lines.append(
        "|----------|-----------|--------|------|-----|-----|-----|"
    )
    for cat, m in sorted(metrics["per_category"].items()):
        lines.append(
            f"| {cat} | {m['precision']:.2%} | {m['recall']:.2%} "
            f"| {m['f1']:.2%} | {m['tp']} | {m['fp']} | {m['fn']} |"
        )

    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

async def main(corpus_path: Path | None = None, output_path: Path | None = None) -> None:
    """Run the full benchmark pipeline and optionally write the report."""
    path = corpus_path or DEFAULT_CORPUS
    if not path.exists():
        print(f"Error: corpus file not found at {path}", file=sys.stderr)
        sys.exit(1)

    logger.info("benchmark_start", corpus=str(path))
    corpus = load_corpus(path)
    raw = await run_benchmark(corpus)
    metrics = compute_metrics(raw)
    report = generate_report(metrics)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")
        logger.info("benchmark_report_written", path=str(output_path))
    else:
        print(report)

    logger.info(
        "benchmark_complete",
        accuracy=metrics["accuracy"],
        total=metrics["total"],
        correct=metrics["correct"],
    )


if __name__ == "__main__":
    args = sys.argv[1:]
    corpus_p = Path(args[0]) if len(args) >= 1 else None
    output_p = Path(args[1]) if len(args) >= 2 else None
    asyncio.run(main(corpus_p, output_p))
