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
    assert 'text: "Awaiting an independent second organization"' in script
    assert "Too early to infer" in script


def test_reporting_stages_are_explicitly_about_the_curated_registry():
    script = source("site/assets/app.js")

    stage = script.split("function reportingStage(entry, board)", 1)[1].split(
        "const BENCHMARK_TASK_SHAPES", 1
    )[0]
    assert "advances / total >= 0.8" in stage
    assert "isNewBenchmark(entry, board) && advances <= 4" in stage
    assert 'label: "Saturated reporting"' in stage
    assert "curated registry" in stage
    assert "convention, not quality" in stage


def test_frontier_svg_fits_the_viewport_without_horizontal_scrolling():
    styles = source("site/assets/styles.css")

    rule = styles.split(".frontier-chart svg {", 1)[1].split("}", 1)[0]
    assert "width: 100%" in rule
    assert "height: auto" in rule
    assert "min-width" not in rule
    assert ".frontier-point-number" in styles


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
