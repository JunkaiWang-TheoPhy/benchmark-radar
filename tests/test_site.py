from html.parser import HTMLParser
from pathlib import Path


class SiteParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[str] = []
        self.ids: set[str] = set()
        self.html_lang = ""
        self.viewport = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        self.tags.append(tag)
        if values.get("id"):
            self.ids.add(str(values["id"]))
        if tag == "html":
            self.html_lang = str(values.get("lang", ""))
        if tag == "meta" and values.get("name") == "viewport":
            self.viewport = True


def test_site_has_accessible_landmarks_and_views():
    parser = SiteParser()
    parser.feed(Path("site/index.html").read_text(encoding="utf-8"))

    assert parser.html_lang == "en"
    assert parser.viewport
    assert {"header", "nav", "main", "footer", "dialog"} <= set(parser.tags)
    assert {"today-view", "trends-view", "explorer-view", "main-content"} <= parser.ids


def test_priority_score_is_reachably_explained():
    html = Path("site/index.html").read_text(encoding="utf-8")
    script = Path("site/assets/app.js").read_text(encoding="utf-8")

    # The score label itself is the affordance, so a reader looking at the
    # number does not have to hunt elsewhere for its definition.
    assert 'id="rubric-dialog"' in html
    assert 'id="rubric-content"' in html
    assert 'id="rubric-nav"' in html
    assert "score-explain" in script
    assert "openRubric" in script
    assert "How is this scored?" in script


def test_rubric_is_read_from_published_data_not_restated_in_the_browser():
    script = Path("site/assets/app.js").read_text(encoding="utf-8")

    # A second hardcoded copy of the weights in the browser is exactly the
    # drift this rubric exists to prevent.
    assert "state.data?.rubrics" in script
    assert "0.40 relevance" not in script
    assert "0.25 evidence" not in script
    for weight in ("0.4 *", "0.25 *", "0.2 *", "0.15 *"):
        assert weight not in script
    assert 'text: "/ 4.00"' not in script


def test_attention_signals_are_not_offered_the_evidence_rubric():
    script = Path("site/assets/app.js").read_text(encoding="utf-8")

    assert "if (!isAttention && state.data?.rubric)" in script


def test_detail_grid_shows_every_component_that_moves_the_total():
    script = Path("site/assets/app.js").read_text(encoding="utf-8")

    for component in ("Priority", "Relevance", "Evidence", "Recency", "Adoption"):
        assert f'["{component}", Number(item.' in script


def test_today_view_keeps_one_signal_summary_and_one_source_status():
    html = Path("site/index.html").read_text(encoding="utf-8")
    script = Path("site/assets/app.js").read_text(encoding="utf-8")

    assert html.count("Ranked evidence") == 1
    assert html.count("Attention signals") == 1
    assert "Daily field note" not in html
    assert "What entered the field?" not in html
    assert "today-overview" not in html
    assert "Sources in results" not in script
    assert "health-summary" not in html


def test_summaries_truncate_at_a_word_boundary():
    script = Path("site/assets/app.js").read_text(encoding="utf-8")

    assert 'const lastSpace = candidate.lastIndexOf(" ");' in script
    assert "candidate.slice(0, lastSpace)" in script


def test_site_does_not_render_source_content_as_html():
    script = Path("site/assets/app.js").read_text(encoding="utf-8")

    assert ".innerHTML" not in script
    assert ".outerHTML" not in script
    assert "document.write" not in script
    assert " eval(" not in script


def test_attention_signals_use_activity_metrics_not_quality_scores():
    script = Path("site/assets/app.js").read_text(encoding="utf-8")

    assert 'text: "Not quality-scored"' in script
    assert '["Submissions", Number(item.metrics?.submissions ?? 1).toLocaleString()]' in script
    assert '["Published", formatDate(item.published_at' in script
    assert "supporting_observations" in script
    assert "total_score: 0" not in script
    assert "evidence_score: 0" not in script


def test_explorer_uses_persisted_attention_and_snapshot_dates():
    script = Path("site/assets/app.js").read_text(encoding="utf-8")
    html = Path("site/index.html").read_text(encoding="utf-8")

    assert "loadExternalFeeds" not in script
    assert "state.external" not in script
    assert "day.attention.observations.map" in script
    assert "snapshot_date: day.date" in script
    assert 'id="kind-filter"' in html


def test_one_snapshot_trend_explains_history_requirement():
    script = Path("site/assets/app.js").read_text(encoding="utf-8")
    styles = Path("site/assets/styles.css").read_text(encoding="utf-8")

    assert "At least two daily snapshots are required to calculate a trend." in script
    assert "dayCount === 1" in script
    assert "[hidden]" in styles
    assert "display: none !important" in styles


def test_supporting_attention_provider_is_not_hard_coded():
    script = Path("site/assets/app.js").read_text(encoding="utf-8")

    assert "`${record.source || item.source} #${record.source_id}`" in script
    assert "Hacker News #${record.source_id}" not in script
