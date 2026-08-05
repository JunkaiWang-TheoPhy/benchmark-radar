"""Stated findings from the adoption and score layers (issue #91).

The issue's third point is that the project kept adding visuals while the real
gap stayed open: "we are doing visual, but still didn't fix most important gap
(the surfacing of insights)". A chart is not a finding. Two charts on one axis
are not a finding either; they are a reader's homework. This module does that
homework in Python, where it can be tested, and hands the dashboard sentences.

WHAT COUNTS AS A FINDING HERE

A finding must be a claim the two layers can actually license, so each one names
the evidence it rests on and each one is refusable by looking at the data. The
interesting cases are exactly the ones a single chart cannot show:

`adopted_without_scores`
    Everyone reports it; nobody's number is readable. The most common state in
    this corpus and the easiest to misread as saturation.
`closing_headroom`
    The best recorded value sits close to the metric's bound. A ceiling claim
    that needs no trend.
`fast_gain`
    A comparable run moved a long way in a short time. Says the instrument was
    not measuring a stable ceiling.
`stale_scores`
    Adoption continued after the last readable score, so the flat right-hand
    side of the chart is a reading gap, not a plateau.
`third_party_only`
    The benchmark's evidence is competitors quoting each other, with no
    first-party number on record.

WHAT IS DELIBERATELY NOT HERE

No finding ranks benchmarks by quality, and none says a benchmark is "solved".
The corpus cannot support either: it is vendor-selected, its scores stop in
mid-2025, and its own file documents which documents could not be read. A module
that emitted "MMLU is saturated" from a flat line would be manufacturing the
misreading the data file spends its header warning against.

Findings are ordered by how much they should change a reader's mind, not by
benchmark rank, so the list opens on the strongest available claim.
"""

from __future__ import annotations

from datetime import date
from typing import Any

# A percent this close to the bound is worth stating as a ceiling observation.
# 5 points is a judgement, not a discovery, and it is written here as one number
# so a reader can disagree with it in one place.
_HEADROOM_POINTS = 5.0

# A comparable run that gained this much inside this window says the instrument
# had room that models took quickly. Both numbers are editorial thresholds.
_FAST_GAIN_POINTS = 15.0
_FAST_GAIN_DAYS = 400

# Adoption continuing this long past the newest readable score makes the score
# line's flat tail a statement about reading coverage rather than capability.
_STALE_SCORE_DAYS = 180

# Ordering, most mind-changing first. `stale_scores` leads because it is the one
# finding that reframes how every chart on the page should be read: a reader who
# takes a flat score tail for a plateau will misread all of them. The
# per-benchmark findings follow, and `adopted_without_scores` comes last of the
# substantive kinds because it reports an absence -- true and worth stating, but
# it changes less than a claim about a number that exists.
_PRIORITY = {
    "stale_scores": 0,
    "closing_headroom": 1,
    "fast_gain": 2,
    "third_party_only": 3,
    "adopted_without_scores": 4,
}


def _days_between(start: str, end: str) -> int:
    return (date.fromisoformat(end) - date.fromisoformat(start)).days


def _count(value: int, singular: str, plural: str | None = None) -> str:
    """Pluralize a counted noun.

    These strings are rendered verbatim, so "1 more reporting documents" is a
    visible defect rather than a cosmetic one: a finding that cannot form a
    sentence undercuts the claim it is making.
    """
    return f"{value} {singular if value == 1 else plural or f'{singular}s'}"


def _latest_card_date(leaderboard: dict[str, Any]) -> str | None:
    dates = [
        card["published"] for card in leaderboard.get("model_cards") or [] if card.get("published")
    ]
    return max(dates) if dates else None


def _adoption_by_id(leaderboard: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {entry["benchmark_id"]: entry for entry in leaderboard.get("entries") or []}


def _finding(
    kind: str,
    *,
    benchmark_id: str,
    name: str,
    headline: str,
    detail: str,
    evidence: str,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "benchmark_id": benchmark_id,
        "benchmark_name": name,
        # One sentence, no hedging, because it is the line the reader sees
        # first. Every qualification lives in `detail` and `evidence`, which are
        # rendered with it rather than behind a disclosure.
        "headline": headline,
        "detail": detail,
        # What in the data licenses the claim. A finding a reader cannot audit
        # is an assertion, and this project's whole posture is that assertions
        # about benchmarks are what it is trying to replace.
        "evidence": evidence,
        "priority": _PRIORITY[kind],
    }


def _adopted_without_scores(
    leaderboard: dict[str, Any],
    progression: dict[str, Any],
    *,
    minimum_organizations: int,
) -> list[dict[str, Any]]:
    scored = set(progression.get("benchmarks") or {})
    unscored = [
        entry
        for entry in leaderboard.get("entries") or []
        if entry["benchmark_id"] not in scored
        and entry["organization_count"] >= minimum_organizations
    ]
    if not unscored:
        return []

    # One finding naming the benchmarks, not one finding per benchmark. The
    # explanation is identical for every one of them -- adoption is known,
    # difficulty is not -- so emitting it six times printed the same paragraph
    # six times and pushed the findings that differ off the first screen. The
    # names carry the specifics that actually vary.
    unscored.sort(key=lambda entry: (-entry["card_count"], entry["name"]))
    named = ", ".join(entry["name"] for entry in unscored)
    leader = unscored[0]
    return [
        _finding(
            "adopted_without_scores",
            # Focuses the most-adopted of them, which is the one whose blank
            # score axis a reader is most likely to go looking for.
            benchmark_id=leader["benchmark_id"],
            name=leader["name"],
            headline=(
                f"{_count(len(unscored), 'benchmark')} reported by at least "
                f"{_count(minimum_organizations, 'organization')} have no readable score "
                f"on record."
            ),
            detail=(
                "Adoption and difficulty are separate questions, and for these only the "
                "first has an answer here. A blank score axis is a limit of what could be "
                "read out of these documents, not a finding about the benchmark. "
                f"They are: {named}."
            ),
            evidence=(
                f"Most-adopted of them is {leader['name']} at "
                f"{_count(leader['card_count'], 'model card')}; the score file records no "
                "verified value for any of them."
            ),
        )
    ]


def _score_findings(
    leaderboard: dict[str, Any],
    progression: dict[str, Any],
) -> list[dict[str, Any]]:
    adoption = _adoption_by_id(leaderboard)
    findings: list[dict[str, Any]] = []

    for benchmark_id, record in (progression.get("benchmarks") or {}).items():
        entry = adoption.get(benchmark_id)
        name = entry["name"] if entry else benchmark_id
        saturation = record["saturation"]
        headroom = saturation["headroom"]

        if headroom is not None and headroom <= _HEADROOM_POINTS:
            findings.append(
                _finding(
                    "closing_headroom",
                    benchmark_id=benchmark_id,
                    name=name,
                    headline=(
                        f"{name}'s best recorded score leaves {headroom:g} points of "
                        f"headroom on a {saturation['bound']:g}-point metric."
                    ),
                    detail=(
                        "This is a statement about the best number on record, not about a "
                        "trend: it holds whether or not anyone reports the benchmark again. "
                        "Remaining headroom is where a metric stops being able to separate "
                        "strong models from each other."
                    ),
                    evidence=(
                        f"{saturation['best_value']:g} {record['metric']} by "
                        f"{saturation['best_model']} ({saturation['best_organization']}), "
                        f"reported {saturation['best_reported_at']}"
                        + (", cited by a third party" if saturation["best_is_third_party"] else "")
                    ),
                )
            )

        gain = saturation["best_gain"]
        if (
            gain
            and gain["improvement"] >= _FAST_GAIN_POINTS
            and 0 < gain["elapsed_days"] <= _FAST_GAIN_DAYS
        ):
            # The headline names the publisher when a run is one vendor's own
            # model line. "AIME moved 40.6 points" reads as a fact about the
            # field; "DeepSeek's own models moved 40.6 points on AIME" is what
            # a two-point single-vendor pair actually shows, and the difference
            # is the entire distinction this dataset is built to preserve.
            single = gain["single_organization"]
            publisher = gain["organization"]
            findings.append(
                _finding(
                    "fast_gain",
                    benchmark_id=benchmark_id,
                    name=name,
                    headline=(
                        (
                            f"{publisher}'s own models moved {gain['improvement']:g} points "
                            f"on {name} in {_count(gain['elapsed_days'], 'day')}."
                        )
                        if single
                        else (
                            f"{name} moved {gain['improvement']:g} points in "
                            f"{_count(gain['elapsed_days'], 'day')} across organizations."
                        )
                    ),
                    detail=(
                        (
                            "One publisher's successive models at an identical instrument and "
                            "protocol, so the move is not an artefact of a changed setup. It "
                            "shows the instrument still had room to discriminate, and it is "
                            "not evidence about other vendors."
                        )
                        if single
                        else (
                            "Models from more than one organization at an identical instrument "
                            "and protocol, so the move is neither one vendor's model line nor "
                            "an artefact of a changed setup."
                        )
                    ),
                    evidence=(
                        f"{gain['from_model']} {gain['from_value']:g} "
                        f"({gain['from_reported_at']}) to {gain['to_model']} "
                        f"{gain['to_value']:g} ({gain['to_reported_at']}), "
                        f"protocol: {gain['protocol']}"
                    ),
                )
            )

        if record["third_party_count"] == record["observation_count"]:
            findings.append(
                _finding(
                    "third_party_only",
                    benchmark_id=benchmark_id,
                    name=name,
                    headline=(
                        f"Every recorded {name} score is a third party quoting someone "
                        f"else's number."
                    ),
                    detail=(
                        "A publisher repeating a competitor's self-reported figure is weaker "
                        "evidence than a vendor reporting its own model, and weaker still "
                        "when the publisher had a stake in the comparison."
                    ),
                    evidence=(
                        f"{record['observation_count']} of {record['observation_count']} "
                        "observations carry a reported_by publisher"
                    ),
                )
            )

    return findings


def _stale_scores(
    leaderboard: dict[str, Any],
    progression: dict[str, Any],
) -> list[dict[str, Any]]:
    """One finding about reading coverage, not one per benchmark.

    Scores in this corpus stop well before mentions do, so the lag holds for
    almost every scored benchmark. Emitting it per benchmark produced nineteen
    near-identical entries that crowded out the findings that distinguish one
    benchmark from another, while saying a single thing nineteen times. It is a
    property of the corpus, so it is stated once, at corpus scope.

    It stays first in the ordering regardless: a reader about to interpret a flat
    score tail as a plateau needs this before any other claim on the page.

    Each lag is measured against the benchmark's *own* latest dated adopter, not
    against the newest card anywhere in the registry. Using the global date let an
    unrelated benchmark's recent card supply the lag: shipped MBPP is only 100
    days behind its own newest adopter and was counted anyway despite the
    threshold, and the published "smallest gap" described a benchmark that was
    never in the set. A claim about one benchmark's reading coverage has to be
    computed from that benchmark's documents.
    """
    records = progression.get("benchmarks") or {}
    if not records:
        return []

    adoption = _adoption_by_id(leaderboard)
    lagging = []
    for benchmark_id, record in records.items():
        entry = adoption.get(benchmark_id)
        if not entry:
            continue
        own_dates = [
            adopter["published"]
            for adopter in entry.get("adopters") or []
            if adopter.get("published")
        ]
        if not own_dates:
            continue
        own_latest = max(own_dates)
        # A later report of *this* benchmark is what makes its flat tail a reading
        # gap rather than the end of its record.
        if own_latest <= record["last_reported_at"]:
            continue
        lag = _days_between(record["last_reported_at"], own_latest)
        if lag < _STALE_SCORE_DAYS:
            continue
        lagging.append((benchmark_id, record, lag, own_latest))
    if not lagging:
        return []

    newest_score = max(record["last_reported_at"] for _, record, _, _ in lagging)
    smallest_lag = min(lag for _, _, lag, _ in lagging)
    newest_relevant_card = max(own_latest for _, _, _, own_latest in lagging)
    return [
        _finding(
            "stale_scores",
            # Corpus scope, so no single benchmark owns it. The empty id is what
            # the renderer keys on to place this above the per-benchmark list
            # instead of attaching it to one chart.
            benchmark_id="",
            name="Reading coverage",
            headline=(
                f"{_count(len(lagging), 'benchmark')} kept gaining reporting documents "
                f"after their last readable score."
            ),
            detail=(
                "Score coverage ends before mention coverage does, so a flat right-hand side "
                "on any of these charts is a reading gap rather than a plateau. Newer cards "
                "do report these benchmarks; their numbers could not be read from the "
                "documents and are absent rather than zero."
            ),
            evidence=(
                f"Newest readable score {newest_score}; newest card reporting one of them "
                f"{newest_relevant_card}; smallest gap {_count(smallest_lag, 'day')}"
            ),
        )
    ]


def build_insights(
    leaderboard: dict[str, Any] | None,
    progression: dict[str, Any] | None,
    *,
    minimum_organizations: int = 4,
    limit: int | None = None,
) -> dict[str, Any] | None:
    """Derive stated findings from the two layers, or nothing if either is absent.

    Returns None rather than an empty document when a layer is missing: the
    dashboard hides the panel entirely in that case, which is honest, whereas an
    empty findings list on the page reads as "we looked and the field is
    uneventful".
    """
    if not leaderboard or not progression:
        return None

    findings = [
        *_stale_scores(leaderboard, progression),
        *_adopted_without_scores(
            leaderboard, progression, minimum_organizations=minimum_organizations
        ),
        *_score_findings(leaderboard, progression),
    ]
    findings.sort(key=lambda item: (item["priority"], item["benchmark_name"], item["kind"]))
    total = len(findings)
    shown = findings if limit is None else findings[:limit]

    return {
        "schema_version": 1,
        "finding_count": total,
        "findings": shown,
        # Announced rather than applied silently, on the same principle the
        # Markdown export truncates by: a list that stops at N with no note
        # reads as a complete account of the corpus.
        "truncated": total > len(shown),
        "measures": (
            "Findings derived from two curated layers: which model cards mention each "
            "benchmark, and which scores could be read verbatim from those documents. "
            "Each finding names the evidence behind it."
        ),
        "does_not_measure": (
            "Benchmark quality, and whether a benchmark is solved. The corpus is "
            "vendor-selected, several documents could not be read, and no score after the "
            "last recorded date is included."
        ),
    }
