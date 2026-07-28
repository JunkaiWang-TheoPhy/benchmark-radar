"""The published scoring rubric, in one place.

`score_item` in `pipeline.py` computes priority from these weights, and
`dashboard_data` copies this module's description into `site/data/radar.json`
so the dashboard can show a reader exactly the rubric that ranked the records
in front of them. Keeping the numbers here rather than restating them in the
browser is deliberate: a rubric the UI describes from its own hardcoded copy
drifts silently the first time a weight changes, and a rubric that says
something the pipeline does not do is worse than no rubric at all.
"""

from __future__ import annotations

from typing import Any

SCORE_MAX = 4.0

# Priority is the weighted mean of the four components below. The weights sum
# to 1.0, so priority shares the components' 0-4 range.
WEIGHTS: dict[str, float] = {
    "relevance": 0.40,
    "evidence": 0.25,
    "recency": 0.20,
    "adoption": 0.15,
}

# Evidence credit per source. A record scores the strongest tier its source
# qualifies for; the tiers are not additive across source families.
EVIDENCE_BASE = 0.5
EVIDENCE_PRIMARY_SOURCES = ("arXiv", "OpenAlex")
EVIDENCE_PRIMARY_CREDIT = 1.5
EVIDENCE_ARTIFACT_SOURCES = ("GitHub", "Hugging Face")
EVIDENCE_ARTIFACT_CREDIT = 1.0
EVIDENCE_AUTHORSHIP_CREDIT = 0.5
EVIDENCE_CROSS_LINK_CREDIT = 0.5

# Relevance credit for taxonomy matches.
RELEVANCE_PER_CATEGORY = 1.25
RELEVANCE_PER_TERM = 0.2
RELEVANCE_TERMS_COUNTED_PER_CATEGORY = 2

# Recency decays linearly from the full score to zero across this many hours.
RECENCY_HALF_LIFE_HOURS = 24.0
RECENCY_ZERO_AT_HOURS = SCORE_MAX * RECENCY_HALF_LIFE_HOURS

# Adoption weights for log10-scaled public counters.
ADOPTION_METRIC_WEIGHTS: dict[str, float] = {
    "stars": 0.8,
    "citations": 0.7,
    "downloads": 0.6,
    "likes": 0.5,
}

COMPONENTS: list[dict[str, Any]] = [
    {
        "key": "relevance",
        "label": "Relevance",
        "weight": WEIGHTS["relevance"],
        "summary": (
            "How squarely the title and the source's own description land inside the "
            "benchmark, evaluation, dataset, and data-quality taxonomy."
        ),
        "bands": [
            f"{RELEVANCE_PER_CATEGORY:.2f} per taxonomy category matched",
            f"{RELEVANCE_PER_TERM:.2f} per matched term, counting up to "
            f"{RELEVANCE_TERMS_COUNTED_PER_CATEGORY} terms per category",
            f"Capped at {SCORE_MAX:.2f}",
        ],
    },
    {
        "key": "evidence",
        "label": "Evidence",
        "weight": WEIGHTS["evidence"],
        "summary": (
            "How directly the record is attested: a primary or structured record "
            "outranks a secondary mention, and named authors and linked artifacts "
            "add attestation."
        ),
        "bands": [
            f"{EVIDENCE_BASE:.2f} baseline for any record that passed ingest",
            f"+{EVIDENCE_PRIMARY_CREDIT:.2f} from a primary scholarly record "
            f"({', '.join(EVIDENCE_PRIMARY_SOURCES)})",
            f"+{EVIDENCE_ARTIFACT_CREDIT:.2f} from a structured artifact registry "
            f"({', '.join(EVIDENCE_ARTIFACT_SOURCES)})",
            f"+{EVIDENCE_AUTHORSHIP_CREDIT:.2f} when the source names authors",
            f"+{EVIDENCE_CROSS_LINK_CREDIT:.2f} when a second artifact URL corroborates it",
            f"Capped at {SCORE_MAX:.2f}",
        ],
    },
    {
        "key": "recency",
        "label": "Recency",
        "weight": WEIGHTS["recency"],
        "summary": (
            "Hours since publication or the last material update, so a revised "
            "record re-enters the day's view."
        ),
        "bands": [
            f"{SCORE_MAX:.2f} at the moment of publication or update",
            f"Decays linearly by 1.00 every {RECENCY_HALF_LIFE_HOURS:g} hours",
            f"Reaches 0.00 at {RECENCY_ZERO_AT_HOURS:g} hours",
        ],
    },
    {
        "key": "adoption",
        "label": "Adoption",
        "weight": WEIGHTS["adoption"],
        "summary": (
            "Public uptake counters on a log10 scale, so the first hundred stars "
            "move the score far more than the ten-thousandth."
        ),
        "bands": [
            f"{weight:.2f} x log10(1 + {metric})"
            for metric, weight in ADOPTION_METRIC_WEIGHTS.items()
        ]
        + [f"Capped at {SCORE_MAX:.2f}"],
    },
]

LIMITS: list[str] = [
    "This is triage for a reader deciding what to open next. It is not peer "
    "review, a quality verdict, or an endorsement.",
    "Relevance reads only the title and the description the source itself "
    "published. Nothing this project writes about a record can earn it points.",
    "Adoption measures attention, not correctness. A widely starred repository "
    "and a careful one are not the same claim.",
    "Attention signals are shown separately and are never scored on this rubric.",
]


def priority_formula() -> str:
    """Render the weighted sum the way the README states it."""
    return " + ".join(
        f"{weight:.2f} {component}"
        for component, weight in ((entry["key"], entry["weight"]) for entry in COMPONENTS)
    )


def rubric_reference(*, minimum_score: float | None = None) -> dict[str, Any]:
    """The rubric as published to the dashboard.

    `minimum_score` is the configured cutoff a record must clear to be reported
    at all. It is part of what the reader is looking at, so it travels with the
    rubric rather than being described separately.
    """
    value: dict[str, Any] = {
        "score_max": SCORE_MAX,
        "formula": priority_formula(),
        "components": [
            {
                "key": entry["key"],
                "label": entry["label"],
                "weight": entry["weight"],
                "summary": entry["summary"],
                "bands": list(entry["bands"]),
            }
            for entry in COMPONENTS
        ],
        "limits": list(LIMITS),
    }
    if minimum_score is not None:
        value["minimum_score"] = float(minimum_score)
    return value
