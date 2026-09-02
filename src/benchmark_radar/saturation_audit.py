"""Protocol-aware saturation audit for report section 6.2."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .benchmark_scores import DEFAULT_SCORES_PATH, build_score_progression
from .model_cards import DEFAULT_REGISTRY_PATH, load_registry

SECTION_6_2_BENCHMARK_IDS = (
    "aime",
    "arena_hard",
    "deepsearchqa",
    "hmmt",
    "math_500",
    "mathvision",
    "swe_bench_verified",
    "tau2_bench",
)

_THRESHOLDS = (5.0, 3.0, 2.0)
_RECOMMENDATIONS = {
    "aime": "replace",
    "arena_hard": "replace",
    "deepsearchqa": "qualify",
    "hmmt": "qualify",
    "math_500": "retain",
    "mathvision": "replace",
    "swe_bench_verified": "replace",
    "tau2_bench": "replace",
}


def _best_row(rows: list[dict[str, Any]], direction: str) -> dict[str, Any]:
    reverse = direction == "higher_is_better"
    return sorted(
        rows,
        key=lambda row: (row["value"], row["reported_at"], row["organization"], row["model"]),
        reverse=reverse,
    )[0]


def _headroom(value: float, *, direction: str, unit: str) -> float | None:
    if unit != "percent":
        return None
    bound = 100.0
    result = bound - value if direction == "higher_is_better" else value
    precision = 0 if float(bound).is_integer() and float(value).is_integer() else 2
    return round(result, precision)


def _series_best(series: dict[str, Any], direction: str) -> dict[str, Any]:
    return _best_row(series["points"], direction)


def _selected_protocol_series(record: dict[str, Any]) -> dict[str, Any] | None:
    direction = record["direction"]
    connectable = [series for series in record["series"] if series["connectable"]]
    if not connectable:
        return None
    return max(
        connectable,
        key=lambda series: (
            _series_best(series, direction)["value"],
            series["dated_points"],
            series["point_count"],
            series["last_reported_at"],
        ),
    )


def _threshold_counts(benchmarks: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts = {}
    for threshold in _THRESHOLDS:
        counts[f"<={int(threshold)}"] = sum(
            1
            for benchmark in benchmarks
            if benchmark[key] is not None and benchmark[key] <= threshold
        )
    return counts


def _document_for(registry: dict[str, Any], source_id: str) -> dict[str, Any]:
    card = next(card for card in registry["model_cards"] if str(card["id"]) == source_id)
    return {
        "id": str(card["id"]),
        "name": str(card.get("name") or card["id"]),
        "url": str(card.get("url") or ""),
        "caveat": str(card.get("caveat") or ""),
    }


def build_saturation_audit(
    progression: dict[str, Any] | None = None,
    registry: dict[str, Any] | None = None,
    *,
    scores_path: Path = DEFAULT_SCORES_PATH,
    registry_path: Path = DEFAULT_REGISTRY_PATH,
) -> dict[str, Any]:
    """Return the source-grounded audit rows for report section 6.2."""

    if registry is None:
        registry = load_registry(registry_path)
    if progression is None:
        progression = build_score_progression(scores_path, registry)

    benchmark_rows: list[dict[str, Any]] = []
    for benchmark_id in SECTION_6_2_BENCHMARK_IDS:
        record = progression["benchmarks"][benchmark_id]
        benchmark_card = next(card for card in registry["benchmarks"] if card["id"] == benchmark_id)
        raw_best = _best_row(record["observations"], record["direction"])
        raw_headroom = record["saturation"]["headroom"]
        selected_series = _selected_protocol_series(record)
        if selected_series is None:
            protocol_headroom = None
            protocol_best = None
        else:
            protocol_best = _series_best(selected_series, record["direction"])
            protocol_headroom = _headroom(
                protocol_best["value"], direction=record["direction"], unit=record["unit"]
            )
        source_ids = sorted({str(row["source_id"]) for row in record["observations"]})
        all_protocols = sorted({str(series["protocol"]) for series in record["series"]})
        all_instruments = sorted({str(series["instrument"]) for series in record["series"]})
        caveat = str(benchmark_card.get("caveat") or "")
        selected_series_key = None
        if selected_series is not None:
            selected_series_key = {
                "instrument": selected_series["instrument"],
                "protocol": selected_series["protocol"],
                "point_count": selected_series["point_count"],
                "dated_points": selected_series["dated_points"],
                "first_reported_at": str(selected_series["first_reported_at"]),
                "last_reported_at": str(selected_series["last_reported_at"]),
                "best_observation_id": protocol_best["observation_id"],
                "best_value": protocol_best["value"],
                "headroom": protocol_headroom,
                "model": protocol_best["model"],
                "organization": protocol_best["organization"],
                "reported_at": str(protocol_best["reported_at"]),
            }

        exclusions = []
        if selected_series is not None:
            selected_ids = {point["observation_id"] for point in selected_series["points"]}
            exclusions = [
                {
                    "observation_id": row["observation_id"],
                    "instrument": row["instrument"],
                    "protocol": row["protocol"],
                    "model": row["model"],
                    "organization": row["organization"],
                    "reported_at": str(row["reported_at"]),
                    "value": row["value"],
                    "reason": "not in the selected protocol-stratified series",
                }
                for row in record["observations"]
                if row["observation_id"] not in selected_ids
            ]

        benchmark_rows.append(
            {
                "benchmark_id": benchmark_id,
                "name": benchmark_card["name"],
                "metric": record["metric"],
                "direction": record["direction"],
                "unit": record["unit"],
                "raw_headroom": raw_headroom,
                "protocol_headroom": protocol_headroom,
                "raw_best": {
                    "observation_id": raw_best["observation_id"],
                    "source_id": raw_best["source_id"],
                    "instrument": raw_best["instrument"],
                    "protocol": raw_best["protocol"],
                    "model": raw_best["model"],
                    "organization": raw_best["organization"],
                    "reported_at": str(raw_best["reported_at"]),
                    "value": raw_best["value"],
                    "read_from": raw_best["read_from"],
                    "reported_by": raw_best["reported_by"],
                },
                "protocol_best": selected_series_key,
                "recommendation": _RECOMMENDATIONS[benchmark_id],
                "source_documents": [
                    _document_for(registry, source_id) for source_id in source_ids
                ],
                "score_ids": [row["observation_id"] for row in record["observations"]],
                "conflicts": [
                    f"instruments: {', '.join(all_instruments)}"
                    if len(all_instruments) > 1
                    else None,
                    f"protocols: {', '.join(all_protocols)}"
                    if len(all_protocols) > 1
                    else None,
                ]
                + ([caveat] if caveat else []),
                "uncertainty": (
                    [
                        "No protocol-stratified series has at least two dated points."
                    ]
                    if selected_series is None
                    else [
                        (
                            "Protocol-stratified comparison uses the strongest connectable "
                            "instrument+protocol series."
                        )
                    ]
                ),
                "exclusions": exclusions,
                "counterexamples": exclusions[:3],
            }
        )

    for benchmark in benchmark_rows:
        benchmark["conflicts"] = [item for item in benchmark["conflicts"] if item]

    return {
        "benchmark_count": len(benchmark_rows),
        "rules": {
            "raw_headroom": "bound minus best published value for the benchmark",
            "protocol_stratified_headroom": (
                "best headroom among connectable instrument+protocol series with at least "
                "two dated points"
            ),
            "protocol_compatibility": (
                "instrument and protocol must both match; otherwise rows are not "
                "comparable"
            ),
            "thresholds": list(_THRESHOLDS),
        },
        "threshold_sensitivity": {
            "raw": _threshold_counts(benchmark_rows, "raw_headroom"),
            "protocol_stratified": _threshold_counts(benchmark_rows, "protocol_headroom"),
        },
        "benchmarks": benchmark_rows,
    }
