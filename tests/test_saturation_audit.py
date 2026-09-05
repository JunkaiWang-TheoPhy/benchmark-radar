import json
from pathlib import Path

from benchmark_radar.saturation_audit import _selected_protocol_series, build_saturation_audit


def test_section_6_2_audit_separates_raw_and_protocol_stratified_headroom() -> None:
    audit = build_saturation_audit()
    rows = {row["benchmark_id"]: row for row in audit["benchmarks"]}

    assert audit["benchmark_count"] == 8
    assert rows["aime"]["raw_headroom"] == 0.8
    assert rows["aime"]["protocol_headroom"] == 20.2
    assert rows["aime"]["recommendation"] == "replace"
    assert rows["hmmt"]["protocol_headroom"] == 4.8
    assert rows["hmmt"]["recommendation"] == "qualify"
    assert rows["math_500"]["recommendation"] == "retain"
    assert rows["swe_bench_verified"]["protocol_headroom"] == 19.4
    assert rows["tau2_bench"]["recommendation"] == "replace"
    assert audit["threshold_sensitivity"]["raw"]["<=5"] == 8
    assert audit["threshold_sensitivity"]["protocol_stratified"]["<=5"] == 1


def test_section_6_2_json_artifact_matches_the_helper() -> None:
    path = Path("docs/technical-report/saturation-audit-6.2.json")
    assert json.loads(path.read_text(encoding="utf-8")) == build_saturation_audit()


def test_unjoinable_observations_are_explicitly_excluded() -> None:
    audit = build_saturation_audit()
    rows = {row["benchmark_id"]: row for row in audit["benchmarks"]}
    for benchmark_id in ("math_500", "mathvision", "tau2_bench"):
        row = rows[benchmark_id]
        assert row["protocol_best"] is None
        assert len(row["exclusions"]) == len(row["score_ids"])
        assert all("no connectable" in item["reason"] for item in row["exclusions"])
    assert rows["swe_bench_verified"]["counterexamples"][0]["value"] == 96.0


def test_lower_is_better_selects_the_lowest_series_best() -> None:
    def series(value: float, key: str) -> dict:
        return {
            "connectable": True,
            "dated_points": 2,
            "point_count": 2,
            "last_reported_at": "2026-08-01",
            "instrument": key,
            "protocol": "p",
            "points": [
                {
                    "value": value,
                    "reported_at": "2026-08-01",
                    "observation_id": key,
                    "organization": key,
                    "model": key,
                }
            ],
        }

    record = {
        "direction": "lower_is_better",
        "series": [series(9.0, "weak"), series(3.0, "strong")],
    }
    assert _selected_protocol_series(record)["instrument"] == "strong"
