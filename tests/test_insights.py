from datetime import date

from benchmark_radar.benchmark_scores import DEFAULT_SCORES_PATH, build_score_progression
from benchmark_radar.insights import build_insights
from benchmark_radar.model_cards import DEFAULT_REGISTRY_PATH, adoption_rank, load_registry


def leaderboard(entries=None, cards=None) -> dict:
    return {
        "entries": entries if entries is not None else [],
        "model_cards": cards if cards is not None else [{"published": "2026-01-01"}],
        "organization_count": 8,
    }


def progression(benchmarks=None) -> dict:
    return {"benchmarks": benchmarks if benchmarks is not None else {}}


def record(**overrides) -> dict:
    value = {
        "metric": "accuracy",
        "observation_count": 2,
        "dated_observation_count": 2,
        "third_party_count": 0,
        "last_reported_at": "2025-01-01",
        "observations": [{"organization": "Org A"}],
        "saturation": {
            "best_value": 60.0,
            "best_model": "Model B",
            "best_organization": "Org A",
            "best_reported_at": "2025-01-01",
            "best_is_third_party": False,
            "bound": 100.0,
            "headroom": 40.0,
            "best_gain": None,
        },
    }
    value.update(overrides)
    return value


def test_no_panel_at_all_when_a_layer_is_missing():
    # An empty findings list on the page reads as "we looked and the field is
    # uneventful", which is a claim this corpus cannot make.
    assert build_insights(None, progression()) is None
    assert build_insights(leaderboard(), None) is None


def test_adopted_but_unscored_benchmarks_are_named_in_one_finding():
    # The explanation is identical for every such benchmark, so repeating it per
    # benchmark printed one paragraph many times and pushed the findings that
    # differ off the first screen. The names are what vary, so they travel in the
    # detail rather than becoming separate cards.
    entries = [
        {
            "benchmark_id": name,
            "name": name.title(),
            "organization_count": 6,
            "card_count": count,
            "adopters": [],
        }
        for name, count in (("alpha", 9), ("beta", 4))
    ]
    insights = build_insights(leaderboard(entries), progression())
    unscored = [item for item in insights["findings"] if item["kind"] == "adopted_without_scores"]
    assert len(unscored) == 1
    assert "2 benchmarks" in unscored[0]["headline"]
    assert "Alpha, Beta" in unscored[0]["detail"]
    # Focuses the most-adopted, whose blank axis a reader is likeliest to seek.
    assert unscored[0]["benchmark_id"] == "alpha"
    assert "9 model cards" in unscored[0]["evidence"]


def test_a_thinly_adopted_unscored_benchmark_is_not_worth_stating():
    # Every registry benchmark lacking a score would otherwise become a finding,
    # burying the ones that distinguish a benchmark from its neighbours.
    entries = [
        {
            "benchmark_id": "alpha",
            "name": "Alpha",
            "organization_count": 1,
            "card_count": 1,
            "adopters": [],
        }
    ]
    insights = build_insights(leaderboard(entries), progression())
    assert insights["findings"] == []


def test_closing_headroom_is_reported_without_a_trend_claim():
    entries = [
        {
            "benchmark_id": "alpha",
            "name": "Alpha",
            "organization_count": 2,
            "card_count": 2,
            "adopters": [],
        }
    ]
    saturation = record()["saturation"] | {"best_value": 98.0, "headroom": 2.0}
    insights = build_insights(
        leaderboard(entries), progression({"alpha": record(saturation=saturation)})
    )
    finding = next(item for item in insights["findings"] if item["kind"] == "closing_headroom")
    assert "2 points of headroom" in finding["headline"]
    # The claim must survive nobody ever reporting the benchmark again.
    assert "not about a trend" in finding["detail"]


def test_a_single_vendor_gain_names_the_vendor_in_the_headline():
    # "AIME moved 40 points" reads as a fact about the field. A two-point
    # single-vendor pair supports only the narrower sentence.
    entries = [
        {
            "benchmark_id": "alpha",
            "name": "Alpha",
            "organization_count": 2,
            "card_count": 2,
            "adopters": [],
        }
    ]
    gain = {
        "instrument": "alpha",
        "protocol": "0-shot",
        "organization": "DeepSeek",
        "from_value": 39.2,
        "to_value": 79.8,
        "from_reported_at": "2024-12-27",
        "to_reported_at": "2025-01-22",
        "from_model": "V3",
        "to_model": "R1",
        "improvement": 40.6,
        "elapsed_days": 26,
        "single_organization": True,
        "dated_points": 2,
    }
    insights = build_insights(
        leaderboard(entries),
        progression({"alpha": record(saturation=record()["saturation"] | {"best_gain": gain})}),
    )
    finding = next(item for item in insights["findings"] if item["kind"] == "fast_gain")
    assert finding["headline"].startswith("DeepSeek's own models moved 40.6 points")
    assert "not evidence about other vendors" in finding["detail"]


def test_reading_coverage_is_stated_once_rather_than_per_benchmark():
    # The lag holds for nearly every scored benchmark in this corpus. Nineteen
    # near-identical entries would crowd out every other finding while saying
    # one thing repeatedly.
    entries = [
        {
            "benchmark_id": name,
            "name": name.title(),
            "organization_count": 2,
            "card_count": 2,
            "adopters": [{"published": "2026-01-01"}],
        }
        for name in ("alpha", "beta", "gamma")
    ]
    benchmarks = {name: record() for name in ("alpha", "beta", "gamma")}
    insights = build_insights(leaderboard(entries), progression(benchmarks))
    stale = [item for item in insights["findings"] if item["kind"] == "stale_scores"]
    assert len(stale) == 1
    assert "3 benchmarks" in stale[0]["headline"]
    # Corpus scope, so it belongs to no single benchmark's chart.
    assert stale[0]["benchmark_id"] == ""


def test_reading_coverage_measures_each_lag_against_its_own_benchmark():
    # Codex P2, third pass. Measuring against the newest card *anywhere* let an
    # unrelated benchmark's recent document supply the lag. Shipped MBPP is only
    # 100 days behind its own newest adopter and was counted anyway, and the
    # published "smallest gap" described a benchmark that was never in the set.
    #
    # `fresh` has a 2026 adopter and belongs. `own_lag_is_small` has a recent score
    # and an adopter only days later, so it must be excluded even though another
    # benchmark's card is a year newer.
    entries = [
        {
            "benchmark_id": "fresh",
            "name": "Fresh",
            "organization_count": 2,
            "card_count": 2,
            "adopters": [{"published": "2026-06-01"}],
        },
        {
            "benchmark_id": "own_lag_is_small",
            "name": "Small",
            "organization_count": 2,
            "card_count": 2,
            "adopters": [{"published": "2025-01-10"}],
        },
    ]
    benchmarks = {
        "fresh": record(last_reported_at="2025-01-01"),
        "own_lag_is_small": record(last_reported_at="2025-01-01"),
    }
    insights = build_insights(leaderboard(entries), progression(benchmarks))
    stale = next(item for item in insights["findings"] if item["kind"] == "stale_scores")
    assert "1 benchmark" in stale["headline"]
    # The reported gap must belong to a benchmark actually in the set.
    assert "516 days" in stale["evidence"]
    assert "2026-06-01" in stale["evidence"]


def test_a_benchmark_with_no_later_report_of_its_own_is_not_stale():
    # Shipped Arena-Hard and Aider Polyglot have no adopter newer than their last
    # score. Nothing about them supports "kept gaining reporting documents".
    entries = [
        {
            "benchmark_id": "alpha",
            "name": "Alpha",
            "organization_count": 2,
            "card_count": 2,
            "adopters": [{"published": "2024-01-01"}],
        }
    ]
    insights = build_insights(
        leaderboard(entries), progression({"alpha": record(last_reported_at="2025-01-01")})
    )
    assert not [item for item in insights["findings"] if item["kind"] == "stale_scores"]


def test_shipped_reading_coverage_excludes_benchmarks_inside_the_threshold():
    # The end-to-end guard. Every benchmark counted must genuinely be at least
    # _STALE_SCORE_DAYS behind a later report of itself.
    registry = load_registry(DEFAULT_REGISTRY_PATH)
    progression_data = build_score_progression(DEFAULT_SCORES_PATH, registry)
    board = adoption_rank(registry)
    insights = build_insights(board, progression_data)
    stale = next(item for item in insights["findings"] if item["kind"] == "stale_scores")

    adoption = {entry["benchmark_id"]: entry for entry in board["entries"]}
    genuinely_lagging = 0
    for benchmark_id, rec in progression_data["benchmarks"].items():
        own = [
            adopter["published"]
            for adopter in adoption.get(benchmark_id, {}).get("adopters") or []
            if adopter.get("published")
        ]
        if not own:
            continue
        latest = max(own)
        if latest > rec["last_reported_at"]:
            lag = (date.fromisoformat(latest) - date.fromisoformat(rec["last_reported_at"])).days
            if lag >= 180:
                genuinely_lagging += 1
    assert f"{genuinely_lagging} benchmarks" in stale["headline"]


def test_reading_coverage_leads_even_against_competing_findings():
    # A reader who takes a flat score tail for a plateau will misread every chart
    # on the page, so this one reframes the others and has to come first. The
    # fixture deliberately also produces an unscored-adoption finding and a
    # headroom finding: an ordering test whose fixture yields one finding proves
    # nothing.
    entries = [
        {
            "benchmark_id": "alpha",
            "name": "Alpha",
            "organization_count": 6,
            "card_count": 9,
            "adopters": [{"published": "2026-01-01"}],
        },
        {
            "benchmark_id": "unscored",
            "name": "Unscored",
            "organization_count": 6,
            "card_count": 9,
            "adopters": [],
        },
    ]
    saturation = record()["saturation"] | {"best_value": 98.0, "headroom": 2.0}
    insights = build_insights(
        leaderboard(entries), progression({"alpha": record(saturation=saturation)})
    )
    kinds = [item["kind"] for item in insights["findings"]]
    assert kinds[0] == "stale_scores"
    # And the competing findings really were produced, so the assertion above
    # was a comparison rather than a walkover.
    assert "closing_headroom" in kinds
    assert "adopted_without_scores" in kinds
    # An absence reported last: it changes less than a claim about a real number.
    assert kinds.index("closing_headroom") < kinds.index("adopted_without_scores")


def test_a_third_party_only_benchmark_is_flagged():
    entries = [
        {
            "benchmark_id": "alpha",
            "name": "Alpha",
            "organization_count": 2,
            "card_count": 2,
            "adopters": [],
        }
    ]
    insights = build_insights(
        leaderboard(entries),
        progression({"alpha": record(third_party_count=2, observation_count=2)}),
    )
    finding = next(item for item in insights["findings"] if item["kind"] == "third_party_only")
    assert "quoting someone else's number" in finding["headline"]


def test_every_finding_carries_auditable_evidence():
    # A finding a reader cannot check is an assertion, and replacing assertions
    # about benchmarks with checkable ones is the point of the project.
    insights = build_insights(
        adoption_rank(load_registry(DEFAULT_REGISTRY_PATH)),
        build_score_progression(DEFAULT_SCORES_PATH, load_registry(DEFAULT_REGISTRY_PATH)),
    )
    assert insights["finding_count"] > 0
    for finding in insights["findings"]:
        assert finding["headline"].endswith(".")
        assert finding["evidence"].strip()
        assert finding["detail"].strip()


def test_the_shipped_findings_never_call_a_benchmark_solved():
    # The corpus is vendor-selected, several documents could not be read, and
    # its scores stop before its mentions do. None of that supports the word.
    insights = build_insights(
        adoption_rank(load_registry(DEFAULT_REGISTRY_PATH)),
        build_score_progression(DEFAULT_SCORES_PATH, load_registry(DEFAULT_REGISTRY_PATH)),
    )
    text = " ".join(
        f"{finding['headline']} {finding['detail']}" for finding in insights["findings"]
    ).lower()
    assert "solved" not in text
    assert "benchmark quality" in insights["does_not_measure"].lower()


def test_counted_nouns_agree_with_their_numbers():
    # These strings render verbatim, so "1 more reporting documents" is a
    # visible defect that undercuts the finding it appears in.
    entries = [
        {
            "benchmark_id": "alpha",
            "name": "Alpha",
            "organization_count": 1,
            "card_count": 1,
            "adopters": [{"published": "2026-01-01"}],
        }
    ]
    insights = build_insights(
        leaderboard(entries), progression({"alpha": record()}), minimum_organizations=1
    )
    text = " ".join(item["headline"] + item["evidence"] for item in insights["findings"])
    assert "1 organizations" not in text
    assert "1 benchmarks" not in text
    assert "1 model cards" not in text
