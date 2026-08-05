"""The rendered half of issue #91: the score track and the stated findings.

Asserts on the shipped site sources the way `test_site.py` and
`test_leaderboard_workbench.py` do. These are guarantees about what a reader
sees, and several of them are honesty guarantees rather than layout ones: the
join rule has to hold in the drawing code, and a flat score tail has to be
labelled as a reading gap rather than left to be read as a plateau.
"""

from pathlib import Path


def source(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_both_readings_share_one_time_axis():
    # The point of the panel. Two charts with independent x scales would not let
    # a reader compare adoption against score at a given date, which is the
    # comparison the issue asked for.
    script = source("site/assets/app.js")
    chart = script.split("function adoptionFrontierChart(entry, board, events)", 1)[1].split(
        "\nfunction clearAdoptionFrontier", 1
    )[0]

    # One x() for both plots, and a score y that offsets below the adoption plot.
    assert "const scoreTop = margin.top + plotHeight + bandGap" in chart
    assert "scoreY(observation.value)" in chart
    assert "x(observation.reported_at)" in chart


def test_the_score_layer_only_draws_lines_the_join_rule_permits():
    # Two values taken under unstated and possibly different conditions are not
    # a measurement of change, so an unconnectable series must draw no line.
    script = source("site/assets/app.js")
    chart = script.split("function adoptionFrontierChart(entry, board, events)", 1)[1].split(
        "\nfunction clearAdoptionFrontier", 1
    )[0]

    assert "if (!series.connectable) continue;" in chart


def test_a_single_vendor_run_is_drawn_as_weaker_evidence():
    script = source("site/assets/app.js")
    styles = source("site/assets/styles.css")

    assert "score-line-single-org" in script
    assert ".score-line-single-org" in styles
    assert "stroke-dasharray" in styles.split(".score-line-single-org", 1)[1][:120]


def test_a_third_party_citation_is_marked_on_the_chart():
    # A publisher repeating a competitor's figure must not read as a first-party
    # report; it is weaker evidence and the chart has to say so.
    script = source("site/assets/app.js")
    styles = source("site/assets/styles.css")

    assert "score-point-third-party" in script
    assert "observation.reported_by" in script
    assert ".score-point-third-party circle" in styles


def test_the_reading_gap_is_labelled_rather_than_drawn_through():
    # Scores in this corpus stop well before mentions do. An unmarked flat tail
    # invites "saturated" as the explanation when "nothing newer could be read"
    # is the actual one.
    script = source("site/assets/app.js")

    assert "no readable score in this window" in script
    assert "score-gap-line" in script


def test_the_score_axis_says_it_is_zoomed():
    # Every value in this corpus sits in the upper part of its scale, so the
    # band is padded around the observed range instead of running 0-100. A
    # zoomed axis that does not say so overstates the movement it shows.
    script = source("site/assets/app.js")

    assert "function scoreBand(record)" in script
    assert "(zoomed)" in script


def test_a_benchmark_with_no_readable_score_says_so_instead_of_plotting_zero():
    script = source("site/assets/app.js")

    readout = script.split("function renderScoreReadout(entry)", 1)[1].split(
        "\nfunction adoptionFrontierChart", 1
    )[0]
    assert "not a zero and not a plateau" in readout
    # And the chart reserves no empty band for it, which would read as a drop.
    chart = script.split("function adoptionFrontierChart(entry, board, events)", 1)[1]
    assert "const scoreHeight = record ? 132 : 0;" in chart


def test_the_evidence_grade_is_printed_not_hidden():
    # The honest scope of a two-point chart is the first thing a reader needs,
    # not an optional disclosure.
    script = source("site/assets/app.js")

    assert "evidence.supports" in script
    assert "evidence.does_not_support" in script
    assert '"Does not support: "' in script


def test_findings_are_rendered_with_their_evidence():
    # Issue #91's third point. A finding a reader cannot audit is an assertion.
    html = source("site/index.html")
    script = source("site/assets/app.js")

    assert 'id="benchmark-findings"' in html
    assert 'id="findings-list"' in html
    assert "function renderBenchmarkFindings(board)" in script
    assert "finding.evidence" in script
    assert "finding.detail" in script


def test_findings_state_what_they_do_not_measure():
    script = source("site/assets/app.js")

    assert "insights.does_not_measure" in script
    assert 'id="findings-limits"' in source("site/index.html")


def test_an_empty_findings_list_hides_the_panel_rather_than_showing_nothing():
    # An empty panel reads as "we looked and the field is uneventful".
    script = source("site/assets/app.js")
    renderer = script.split("function renderBenchmarkFindings(board)", 1)[1].split(
        "\nfunction modelCardLabelCounts", 1
    )[0]

    assert "panel.hidden = true" in renderer
    assert "!insights.findings?.length" in renderer


def test_a_finding_can_move_the_chart_to_the_benchmark_it_is_about():
    # A claim should never be more than one interaction away from its data.
    script = source("site/assets/app.js")
    card = script.split("function findingCard(finding, board)", 1)[1].split(
        "\nfunction renderBenchmarkFindings", 1
    )[0]

    assert "state.lfrontier = target.benchmark_id" in card
    assert "renderAdoptionFrontier(board)" in card
    # Corpus-scope findings name no benchmark, so there is nothing to focus.
    assert "finding.benchmark_id" in card


def test_the_explainer_still_separates_reporting_from_score_saturation():
    # The guarantee that predates this change and must survive it: a flat
    # adoption run is reporting saturation within a curated registry, and is not
    # a claim about the benchmark's scores.
    html = " ".join(source("site/index.html").split())

    assert "A long flat run is reporting saturation" in html
    assert "not a claim about benchmark score saturation" in html
    assert "connected only where the instrument and protocol" in html


def test_the_score_layer_is_keyed_by_the_same_benchmark_id_as_adoption():
    # Two rankings that could disagree about what a benchmark is would be worse
    # than one. The score layer is a lookup, not a second ordering.
    script = source("site/assets/app.js")

    assert "benchmark_score_progression?.benchmarks?.[benchmarkId]" in script
