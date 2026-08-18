from pathlib import Path


def source(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_frontier_opens_on_a_new_signal_with_three_dated_organizations():
    script = source("site/assets/app.js")

    default_entry = script.split("function frontierDefaultEntry(board)", 1)[1].split(
        "function reportingStage", 1
    )[0]
    assert "isNewBenchmark(entry, board)" in default_entry
    assert "frontierAdvances(entry).length >= 3" in default_entry
    assert "sharedSignals.length ? sharedSignals : adopted" in default_entry


def test_one_organization_history_uses_milestones_instead_of_an_empty_plot():
    html = source("site/index.html")
    script = source("site/assets/app.js")

    assert 'id="frontier-milestones"' in html
    assert "frontier.length < 2" in script
    assert 'className: "frontier-sparse"' in script
    assert 'text: t("Awaiting an independent second organization")' in script
    assert "Too early to infer" in script


def test_reporting_stages_are_explicitly_about_the_curated_registry():
    script = source("site/assets/app.js")

    stage = script.split("function reportingStage(entry, board)", 1)[1].split(
        "const BENCHMARK_TASK_SHAPES", 1
    )[0]
    assert "advances / total >= 0.8" in stage
    assert "isNewBenchmark(entry, board) && advances <= 4" in stage
    assert 'label: t("Saturated reporting")' in stage
    assert "curated registry" in stage
    assert "convention, not quality" in stage


def test_frontier_svg_fits_the_viewport_without_horizontal_scrolling():
    styles = source("site/assets/styles.css")

    rule = styles.split(".frontier-chart svg {", 1)[1].split("}", 1)[0]
    assert "width: 100%" in rule
    assert "height: auto" in rule
    assert "min-width" not in rule
    # The marker styling this used to check (`.frontier-point-number`) is gone with
    # the numbers themselves; the advance marker is now a brand-colored circle
    # carrying the reporting organization's glyph (issue #178).
    assert ".frontier-point-face" in styles


def test_trajectory_points_expose_and_pin_record_details():
    script = source("site/assets/app.js")
    styles = source("site/assets/styles.css")

    assert 'className: "frontier-tooltip"' in script
    assert 'role: "tooltip"' in script
    assert 'group.addEventListener("pointerenter", () =>' in script
    assert 'group.addEventListener("click"' in script
    assert 'event.key === "Escape"' in script
    assert 'classList.add("is-selected")' in script
    assert '"aria-pressed": "false"' in script
    assert 'label: t("Protocol")' in script
    assert 'label: t("Source")' in script
    assert ".frontier-point.is-selected .frontier-point-face" in styles
    assert ".score-point.is-selected .score-point-face" in styles
    assert "pinned: selectedFrontierPoint === group" in script
    assert 'record.unit === "percent" ? "%" : ` ${record.unit}`' in script
    assert 'role: "group"' in script
    assert 'event.key === "Escape" && selectedFrontierPoint' in script
    assert 'view !== "leaderboard" && selectedFrontierPoint' in script
    assert 'pinned ? "dialog" : "tooltip"' in script
    assert 'text: t("Open source record ↗")' in script
    assert 'byId("frontier-tooltip").querySelector("a")?.focus()' in script
    assert "tooltip?.contains(document.activeElement)" in script
    assert "if (focused) show()" in script
    assert "else if (hovered)" in script
    assert "if (selectedFrontierPoint === group)" in script
    assert "clearFrontierPointSelection();" in script.split("function openRubric", 1)[1]
    assert "function enableFrontierTouchTargets(svg)" in script
    assert "nearestDistance <= 22" in script
    assert 'window.addEventListener("resize", repositionFrontierTooltip)' in script
    assert 'window.addEventListener("scroll", repositionFrontierTooltip' in script
    assert 'kind: event.advances ? "First report card" : "Repeat report card"' in script
    assert ".card-rug-tick.is-selected line" in styles
    assert "pointer-events: none" in styles
    assert ".frontier-tooltip.is-pinned" in styles
    assert "function scoreOnlyChart(entry, board)" in script
    assert "scoreOnlyChart(entry, board)" in script
    assert "`${event.organization} · ${event.model} · first report · count" not in script
    assert "`${observation.model} · ${observation.value} · ${observation.protocol}`" not in script


def test_score_legend_explains_solid_and_dashed_connections():
    script = source("site/assets/app.js")
    styles = source("site/assets/styles.css")

    assert '"legend-swatch-score-line",' in script
    assert '"Solid score connection"' in script
    assert '"same instrument and protocol across organizations"' in script
    assert '"legend-swatch-score-line-single-org",' in script
    assert '"Dashed score connection"' in script
    assert '"same instrument and protocol, one organization only"' in script
    assert ".legend-swatch-score-line-single-org" in styles
    assert "border-top-style: dashed" in styles


def test_task_preview_distinguishes_source_paraphrase_from_domain_fallback():
    html = source("site/index.html")
    script = source("site/assets/app.js")

    assert 'id="frontier-task-preview"' in html
    assert "BENCHMARK_TASK_SHAPES[entry.benchmark_id]" in script
    assert "TASK_SHAPES[entry.domain]" in script
    assert '"Source-paraphrased task shape"' in script
    assert '"Representative task shape"' in script
    assert "Not a verbatim benchmark item" in script
    assert 'rel: "noopener noreferrer"' in script


def test_workbench_states_the_schema_needed_for_a_true_pareto_frontier():
    html = source("site/index.html")
    normalized = " ".join(html.split())

    assert "What would make this a true Pareto frontier?" in normalized
    for field in (
        "benchmark version and split",
        "metric direction",
        "harness or scaffold",
        "reasoning budget",
        "cost or latency",
    ):
        assert field in normalized
    assert "Only compatible configurations" in normalized
    assert "connect only nondominated observations" in normalized
    assert "publication-time slider" in normalized


def test_apex_agents_links_to_its_actual_paper():
    registry = source("data/model_cards.yml")
    apex = registry.split("  - id: apex_agents", 1)[1].split("\n  - id:", 1)[0]

    assert "https://arxiv.org/abs/2601.14242" in apex
    assert "released: 2026-01-20" in apex
    assert "2512.02141" not in apex


def test_issue_240_sections_default_collapsed_but_visible():
    # "Benchmarks by model card adoption", "Model cards in the registry", and
    # "What the two layers say - Stated findings" are <details> with no `open`:
    # present on first load, closed until the reader asks.
    html = source("site/index.html")

    assert '<details class="findings-panel" id="benchmark-findings"' in html
    assert '<details class="trend-panel adoption-table" id="adoption-table">' in html
    assert '<details class="ledger" aria-labelledby="leaderboard-cards-heading">' in html
    assert 'id="benchmark-findings" open' not in html
    assert 'adoption-table" open' not in html
    assert 'class="ledger" open' not in html

    # The empty-findings behaviour is unchanged: hidden entirely, since an
    # empty panel reads as "we looked and the field is uneventful". Collapsed
    # by default applies only when findings exist.
    script = source("site/assets/app.js")
    renderer = script.split("function renderBenchmarkFindings(board)", 1)[1].split(
        "\nfunction modelCardLabelCounts", 1
    )[0]
    assert "panel.hidden = true" in renderer
    assert "panel.hidden = false" in renderer
