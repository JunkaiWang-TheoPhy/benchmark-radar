"""Small, explicit relevance contract for the shipped lexical catalog.

These cases test user-visible intent, not implementation scores. A source
refresh may add a genuinely relevant benchmark, but it must never turn an OOD
query into a page of one-token accidents. Review changed expectations against
the underlying benchmark records instead of mechanically updating snapshots.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from benchmark_radar.query import QueryService

FIXTURE_PATH = Path("tests/fixtures/search_relevance.yml")
FIXTURE = yaml.safe_load(FIXTURE_PATH.read_text(encoding="utf-8"))
CASES = FIXTURE["cases"]
POSITIVE_CASES = [case for case in CASES if case["kind"] == "topical"]
NO_ANSWER_CASES = [case for case in CASES if case["kind"] == "no_answer"]


def test_relevance_fixture_has_a_stable_schema_and_unique_ids() -> None:
    assert FIXTURE["schema_version"] == 1
    ids = [case["id"] for case in CASES]
    assert len(ids) == len(set(ids))
    assert POSITIVE_CASES
    assert NO_ANSWER_CASES


@pytest.mark.parametrize(
    "case",
    POSITIVE_CASES,
    ids=lambda case: case["id"],
)
def test_positive_queries_surface_known_relevant_records(case: dict) -> None:
    result = QueryService().search(case["query"], scope=case["scope"], limit=20)
    returned = {record["name"] for record in result["results"]}

    assert result["search_status"] == "matches_found"
    assert set(case["must_include"]) <= returned
    assert all(record["match"]["query_coverage"] == 1.0 for record in result["results"])


@pytest.mark.parametrize(
    "case",
    NO_ANSWER_CASES,
    ids=lambda case: case["id"],
)
def test_no_answer_queries_abstain_instead_of_returning_partial_noise(case: dict) -> None:
    result = QueryService().search(case["query"], scope=case["scope"], limit=20)

    assert result["search_status"] == "no_matches_above_threshold"
    assert result["total_matches"] == 0
    assert result["results"] == []


def test_opencompass_source_text_makes_opaque_names_discoverable() -> None:
    result = QueryService().search("scientific fact checking charts", scope="catalog", limit=5)

    assert result["results"][0]["name"] == "ClimateViz"
    assert result["results"][0]["source"] == "opencompass_hub"
    assert result["results"][0]["match"]["matched_tokens"] == [
        "charts",
        "checking",
        "fact",
        "scientific",
    ]


def test_single_token_name_search_never_returns_an_empty_token_explanation() -> None:
    result = QueryService().search("CASP", scope="all", limit=20)

    assert all(record["match"]["matched_tokens"] for record in result["results"])
