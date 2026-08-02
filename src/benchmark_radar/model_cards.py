"""Model Card Adoption Rank: which benchmarks frontier model cards actually report.

Issue #83 asked for a queryable registry of every benchmark result in every
model card, keyed by evaluation configuration. That is the right destination and
the wrong first step: it cannot produce a single row until a per-vendor PDF
parser exists, and every row it did produce would carry a score that is
incomparable to the score beside it.

This module implements the tractable core of that idea. It counts *mentions*,
not scores. A mention is the one fact that survives the configuration caveats
the issue itself raises: it does not matter whether a card ran AIME at pass@1 or
consensus@64 with a Python tool, the card still chose to put AIME in front of
its readers. Adoption is therefore a claim about vendor attention, and this
module is careful never to present it as a claim about benchmark quality.

The counted unit is the document, not the result row. A card reporting AIME in
four configurations adds one to AIME's adoption count, exactly like a card
reporting it once, so a verbose appendix cannot outvote a different vendor.
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

import yaml

# The single date format JavaScript's Date constructor parses reliably. See
# `_require_date` for why the ISO 8601 standard is too wide a target here.
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")

REGISTRY_SCHEMA_VERSION = 1

DEFAULT_REGISTRY_PATH = Path("data/model_cards.yml")

# Domains carry no ordering: `math` is not above or below `coding`. They exist
# so a reader can ask "what does this field measure" without the leaderboard
# implying a hierarchy between fields.
_REQUIRED_BENCHMARK_FIELDS = ("id", "name", "domain")
_REQUIRED_CARD_FIELDS = ("id", "organization", "model", "url", "benchmarks")


class ModelCardRegistryError(ValueError):
    """Raised when the curated registry is internally inconsistent."""


def _require(value: Any, fields: tuple[str, ...], *, label: str) -> None:
    if not isinstance(value, dict):
        raise ModelCardRegistryError(f"{label} must be a mapping")
    missing = [field for field in fields if not value.get(field)]
    if missing:
        raise ModelCardRegistryError(f"{label} is missing fields: {', '.join(missing)}")


def _require_date(value: Any, *, label: str) -> None:
    """Reject a date the browser cannot format.

    These values reach `Intl.DateTimeFormat` unmodified, and it throws a
    RangeError on an unparseable one. The dashboard's initialization catch
    treats that as an unusable data file and hides *every* view, so a single
    typo in one optional field would take Today and Trends down with the
    leaderboard. Failing the build here keeps that blast radius at zero.

    `date.fromisoformat` alone is too permissive to protect that: on Python
    3.11+ it also accepts `20250807` and `2025-W32-4`, both of which are valid
    ISO 8601 and both of which JavaScript's Date parses to Invalid Date. The
    check is therefore against the one format the browser accepts, not against
    the standard.
    """
    if isinstance(value, date):
        return
    text = str(value)
    if not _ISO_DATE.fullmatch(text):
        raise ModelCardRegistryError(f"{label} must be an ISO date (YYYY-MM-DD)")
    try:
        date.fromisoformat(text)
    except ValueError as error:
        raise ModelCardRegistryError(f"{label} is not a real calendar date") from error


def load_registry(path: Path = DEFAULT_REGISTRY_PATH) -> dict[str, Any]:
    """Read and validate the curated model card registry.

    Validation is strict on purpose. The leaderboard's only claim is "this many
    distinct cards reported this benchmark", and a benchmark id that appears in
    a card but not in the benchmark block would silently create a phantom entry
    with an adoption count of one. That is indistinguishable from a real
    benchmark nobody adopted, so it is rejected rather than tolerated.
    """
    if not path.exists():
        raise ModelCardRegistryError(f"{path}: registry file not found")
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ModelCardRegistryError(f"{path}: registry must be a mapping")
    version = document.get("schema_version")
    if version != REGISTRY_SCHEMA_VERSION:
        raise ModelCardRegistryError(f"{path}: unsupported schema_version {version!r}")

    benchmarks = document.get("benchmarks")
    cards = document.get("model_cards")
    if not isinstance(benchmarks, list) or not benchmarks:
        raise ModelCardRegistryError(f"{path}: benchmarks must be a non-empty array")
    if not isinstance(cards, list) or not cards:
        raise ModelCardRegistryError(f"{path}: model_cards must be a non-empty array")

    by_id: dict[str, dict[str, Any]] = {}
    for index, benchmark in enumerate(benchmarks):
        _require(benchmark, _REQUIRED_BENCHMARK_FIELDS, label=f"{path}: benchmark {index}")
        benchmark_id = str(benchmark["id"])
        if benchmark_id in by_id:
            raise ModelCardRegistryError(f"{path}: duplicate benchmark id {benchmark_id!r}")
        by_id[benchmark_id] = benchmark

    seen_cards: set[str] = set()
    for index, card in enumerate(cards):
        _require(card, _REQUIRED_CARD_FIELDS, label=f"{path}: model card {index}")
        card_id = str(card["id"])
        if card_id in seen_cards:
            raise ModelCardRegistryError(f"{path}: duplicate model card id {card_id!r}")
        seen_cards.add(card_id)
        if not isinstance(card["benchmarks"], list):
            raise ModelCardRegistryError(
                f"{path}: model card {card_id!r} benchmarks must be a list"
            )
        unknown = sorted({str(ref) for ref in card["benchmarks"]} - by_id.keys())
        if unknown:
            raise ModelCardRegistryError(
                f"{path}: model card {card_id!r} references unknown benchmarks: "
                f"{', '.join(unknown)}"
            )
        if not str(card["url"]).startswith(("https://", "http://")):
            raise ModelCardRegistryError(f"{path}: model card {card_id!r} url must be HTTP(S)")
        for field in ("published", "retrieved_at"):
            if card.get(field):
                _require_date(card[field], label=f"{path}: model card {card_id!r} {field}")

    return {"benchmarks": benchmarks, "model_cards": cards}


def adoption_rank(registry: dict[str, Any]) -> dict[str, Any]:
    """Rank benchmarks by how many distinct model cards report them.

    Two counts are published side by side and neither is the "real" one:

    ``card_count``
        How many documents report the benchmark. This is the headline: it is
        what "popular in model cards" literally means.
    ``organization_count``
        How many distinct publishers report it. A benchmark carried by six
        cards from one vendor is a house style; the same six cards from six
        vendors is a shared standard. Ranking on cards alone cannot tell those
        apart, so the organization count breaks ties and is shown next to the
        headline rather than folded into it.

    Ordering is total and deterministic: cards, then organizations, then name.
    No score is combined out of the two, because any weighting would be an
    invented judgement presented as a measurement.
    """
    cards = registry["model_cards"]
    benchmarks = {str(benchmark["id"]): benchmark for benchmark in registry["benchmarks"]}

    card_counts: Counter[str] = Counter()
    organizations: dict[str, set[str]] = {}
    adopters: dict[str, list[dict[str, Any]]] = {}

    for card in cards:
        organization = str(card["organization"])
        # A set: a card listing the same benchmark twice, or listing two
        # aliases that resolve to one id, still counts once.
        for benchmark_id in sorted({str(ref) for ref in card["benchmarks"]}):
            card_counts[benchmark_id] += 1
            organizations.setdefault(benchmark_id, set()).add(organization)
            adopters.setdefault(benchmark_id, []).append(
                {
                    "model_card_id": str(card["id"]),
                    "organization": organization,
                    "model": str(card["model"]),
                    "document_type": str(card.get("document_type") or "model_card"),
                    "published": str(card["published"]) if card.get("published") else None,
                    "url": str(card["url"]),
                }
            )

    total_cards = len(cards)
    entries = []
    for benchmark_id, benchmark in benchmarks.items():
        count = card_counts.get(benchmark_id, 0)
        entries.append(
            {
                "benchmark_id": benchmark_id,
                "name": str(benchmark["name"]),
                "domain": str(benchmark["domain"]),
                "url": str(benchmark.get("url") or "") or None,
                "aliases": [str(alias) for alias in benchmark.get("aliases") or []],
                # The caveat travels with the row. A ranking that shows MMLU
                # high and does not say "saturated and contaminated" invites
                # exactly the reading issue #83 warns against.
                "caveat": (str(benchmark["caveat"]).strip() if benchmark.get("caveat") else None),
                "card_count": count,
                "organization_count": len(organizations.get(benchmark_id, set())),
                "organizations": sorted(organizations.get(benchmark_id, set())),
                "adoption_share": round(count / total_cards, 4) if total_cards else 0.0,
                "adopters": sorted(
                    adopters.get(benchmark_id, []),
                    key=lambda entry: (
                        entry["organization"],
                        entry["published"] or "",
                        entry["model"],
                    ),
                ),
            }
        )

    entries.sort(
        key=lambda entry: (
            -entry["card_count"],
            -entry["organization_count"],
            entry["name"],
        )
    )
    for position, entry in enumerate(entries, start=1):
        entry["rank"] = position

    organization_totals = Counter(str(card["organization"]) for card in cards)
    domain_totals = Counter(entry["domain"] for entry in entries if entry["card_count"])

    return {
        "schema_version": REGISTRY_SCHEMA_VERSION,
        "model_card_count": total_cards,
        "benchmark_count": len(entries),
        "organization_count": len(organization_totals),
        "organizations": dict(sorted(organization_totals.items())),
        "domains": dict(sorted(domain_totals.items())),
        # Sorted by publisher then date so the model list reads as a roster
        # rather than as a second, implied ranking.
        "model_cards": sorted(
            (
                {
                    "model_card_id": str(card["id"]),
                    "organization": str(card["organization"]),
                    "model": str(card["model"]),
                    "document_type": str(card.get("document_type") or "model_card"),
                    "published": str(card["published"]) if card.get("published") else None,
                    "url": str(card["url"]),
                    "retrieved_at": (
                        str(card["retrieved_at"]) if card.get("retrieved_at") else None
                    ),
                    "benchmark_count": len({str(ref) for ref in card["benchmarks"]}),
                    "benchmarks": sorted({str(ref) for ref in card["benchmarks"]}),
                }
                for card in cards
            ),
            key=lambda card: (card["organization"], card["published"] or "", card["model"]),
        ),
        "entries": entries,
        # Stated in the data rather than only in the UI, so any consumer of
        # radar.json inherits the caveat instead of re-deriving the ranking's
        # meaning from its column headers.
        "measures": (
            "How many curated model cards report each benchmark. This measures "
            "vendor attention, not benchmark quality: a saturated or contaminated "
            "benchmark can rank highly precisely because it is conventional to "
            "report it."
        ),
    }


def build_adoption_rank(path: Path = DEFAULT_REGISTRY_PATH) -> dict[str, Any]:
    return adoption_rank(load_registry(path))
