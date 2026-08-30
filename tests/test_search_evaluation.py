from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from benchmark_radar.query import QueryService
from benchmark_radar.search_evaluation import evaluate, load_dataset

DATASET_PATH = Path("tests/fixtures/search_evaluation.yml")


@pytest.fixture(scope="module")
def evaluation_report() -> dict:
    return evaluate(QueryService(), load_dataset(DATASET_PATH))


def test_search_evaluation_dataset_is_explicit_and_not_self_scoring() -> None:
    # Regression: treating every unlisted result as negative makes sparse judgments
    # look like complete labels and produces misleading precision or NDCG numbers.
    dataset = load_dataset(DATASET_PATH)

    assert "Unlisted records are unjudged, not negative" in dataset["description"]
    assert {case["kind"] for case in dataset["queries"]} == {
        "catalog_gap",
        "navigational",
        "topical",
    }
    assert all("relevant_keys" in case for case in dataset["queries"])
    assert all(case["intent"].strip() for case in dataset["queries"])


def test_search_evaluation_rejects_duplicate_query_ids(tmp_path: Path) -> None:
    # Regression: duplicate IDs made a changed query look like the same stable
    # evaluation case in review output, hiding which judgment actually moved.
    dataset = yaml.safe_load(DATASET_PATH.read_text(encoding="utf-8"))
    dataset["queries"][1]["id"] = dataset["queries"][0]["id"]
    path = tmp_path / "duplicate.yml"
    path.write_text(yaml.safe_dump(dataset), encoding="utf-8")

    with pytest.raises(ValueError, match="id must be a unique non-empty string"):
        load_dataset(path)


def test_search_evaluation_meets_versioned_quality_thresholds(evaluation_report: dict) -> None:
    # Regression: a ranking tweak that improves one demo query can silently move
    # known navigational and topical answers below the agent's retrieval window.
    report = evaluation_report

    assert report["query_count"] == 18
    assert report["positive_query_count"] == 14
    assert report["catalog_gap_query_count"] == 4
    assert report["passed"], report["failures"]


def test_gap_queries_have_no_unreviewed_full_match_in_the_evaluation_window(
    evaluation_report: dict,
) -> None:
    # Regression: source refreshes can make a former Catalog gap appear fully
    # matched in the agent's top-20 window; that requires a relevance review.
    report = evaluation_report
    gap_cases = [case for case in report["cases"] if "full_match_keys" in case]

    assert gap_cases
    assert all(not case["full_match_keys"] for case in gap_cases)


def test_gap_queries_retain_reviewed_partial_candidates_for_agent_judgment(
    evaluation_report: dict,
) -> None:
    # Regression: the all-terms gate scored perfectly on gap abstention while
    # deleting the partial lexical evidence the agent was supposed to inspect.
    report = evaluation_report
    gap_cases = [case for case in report["cases"] if "full_match_keys" in case]
    expected_cases = [case for case in gap_cases if case["partial_retention_at_20"] is not None]

    assert expected_cases
    assert all(case["partial_retention_at_20"] == 1.0 for case in expected_cases)
    assert all(not case["missing_expected_partial_keys"] for case in expected_cases)
