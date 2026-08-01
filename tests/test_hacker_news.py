import json
from datetime import UTC, datetime
from pathlib import Path

from benchmark_radar.hacker_news import (
    cluster_observations,
    collect_hacker_news,
    match_categories,
    normalized_title,
)


def config():
    return {
        "lookback_hours": 168,
        "items_per_query": 40,
        "queries": ["AI benchmark", "LLM evaluation"],
        "taxonomy": {
            "benchmark": ["benchmark", "leaderboard", "challenge set"],
            "evaluation": ["evaluation", "eval", "judge model"],
            "dataset": ["dataset", "corpus"],
        },
    }


def fixture_fetcher(_url, _params):
    return json.loads(Path("tests/fixtures/hn.json").read_text(encoding="utf-8"))


def test_public_collector_emits_clustered_attention_observation():
    observations, health = collect_hacker_news(
        config(),
        datetime(2026, 7, 27, 12, tzinfo=UTC),
        fetcher=fixture_fetcher,
    )

    assert health == {
        "source": "Hacker News",
        "ok": True,
        "item_count": 1,
        "error": None,
    }
    assert len(observations) == 1
    observation = observations[0]
    assert observation["id"] == "hacker-news:12345"
    assert observation["url"] == "https://news.ycombinator.com/item?id=12345"
    assert observation["primary_artifact_url"] == "https://example.org/benchmark"
    assert observation["categories"] == ["benchmark", "evaluation"]
    assert observation["metrics"] == {
        "comments": 12.0,
        "points": 43.0,
        "submissions": 2.0,
    }
    assert observation["supporting_observations"] == [
        {
            "source_id": "12346",
            "url": "https://news.ycombinator.com/item?id=12346",
            "published_at": "2026-07-27T09:00:00+00:00",
            "metrics": {"points": 1.0, "comments": 0.0},
            "primary_artifact_url": "https://mirror.example.org/benchmark",
        }
    ]
    assert any("not scientific-quality evidence" in value for value in observation["rationale"])
    assert any("Clustered 2 public submissions" in value for value in observation["rationale"])


def test_title_normalization_is_exact_but_punctuation_insensitive():
    assert normalized_title("DeepSWE – Best Benchmark?") == normalized_title(
        "DeepSWE: Best Benchmark!"
    )


def test_category_terms_are_anchored_at_word_starts():
    taxonomy = {"evaluation": ["eval"], "dataset": ["dataset"]}

    assert match_categories("A retrieval dataset", taxonomy) == ["dataset"]
    assert match_categories("An evaluation dataset", taxonomy) == ["dataset", "evaluation"]


def test_cluster_identity_does_not_change_with_engagement():
    def observation(source_id, points):
        return {
            "id": f"hacker-news:{source_id}",
            "source": "Hacker News",
            "source_id": source_id,
            "title": "The same benchmark",
            "url": f"https://news.ycombinator.com/item?id={source_id}",
            "published_at": f"2026-07-27T0{source_id}:00:00+00:00",
            "categories": ["benchmark"],
            "metrics": {"points": points, "comments": 0},
            "rationale": [],
        }

    first = cluster_observations([observation("1", 10), observation("2", 5)])[0]
    later = cluster_observations([observation("1", 10), observation("2", 15)])[0]
    preserved = cluster_observations(
        [observation("1", 10), observation("2", 15)],
        preferred_source_ids={"2"},
    )[0]

    assert first["id"] == later["id"] == "hacker-news:1"
    assert preserved["id"] == "hacker-news:2"


def test_empty_result_is_healthy():
    observations, health = collect_hacker_news(
        config(),
        datetime(2026, 7, 27, 12, tzinfo=UTC),
        fetcher=lambda _url, _params: {"hits": []},
    )

    assert observations == []
    assert health["ok"] is True
    assert health["item_count"] == 0


def test_failure_does_not_look_like_empty_success():
    def fail(_url, _params):
        raise TimeoutError("fixture timeout")

    observations, health = collect_hacker_news(
        config(),
        datetime(2026, 7, 27, 12, tzinfo=UTC),
        fetcher=fail,
    )

    assert observations == []
    assert health["ok"] is False
    assert "TimeoutError" in health["error"]


def test_malformed_search_response_is_a_visible_failure():
    observations, health = collect_hacker_news(
        config(),
        datetime(2026, 7, 27, 12, tzinfo=UTC),
        fetcher=lambda _url, _params: {},
    )

    assert observations == []
    assert health["ok"] is False
    assert "hits array" in health["error"]


def test_stories_newer_than_collection_time_are_excluded():
    observations, health = collect_hacker_news(
        config(),
        datetime(2026, 7, 27, 12, tzinfo=UTC),
        fetcher=lambda _url, _params: {
            "hits": [
                {
                    "objectID": "future",
                    "title": "A future AI benchmark",
                    "created_at": "2026-07-28T12:00:00Z",
                }
            ]
        },
    )

    assert observations == []
    assert health["ok"] is True
