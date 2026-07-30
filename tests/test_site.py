from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit


class SiteParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[str] = []
        self.ids: set[str] = set()
        self.html_lang = ""
        self.viewport = False
        self.local_refs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        self.tags.append(tag)
        if values.get("id"):
            self.ids.add(str(values["id"]))
        if tag == "html":
            self.html_lang = str(values.get("lang", ""))
        if tag == "meta" and values.get("name") == "viewport":
            self.viewport = True
        reference = values.get("href") or values.get("src")
        if reference and not urlsplit(reference).scheme and not reference.startswith(("#", "//")):
            self.local_refs.append(reference)


def test_site_has_accessible_landmarks_and_views():
    parser = SiteParser()
    parser.feed(Path("site/index.html").read_text(encoding="utf-8"))

    assert parser.html_lang == "en"
    assert parser.viewport
    assert {"header", "nav", "main", "footer", "dialog"} <= set(parser.tags)
    assert {"today-view", "trends-view", "map-view", "main-content"} <= parser.ids
    assert "explorer-view" not in parser.ids


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


def test_scan_date_select_is_not_reset_by_the_shared_filters_input_handler():
    script = Path("site/assets/app.js").read_text(encoding="utf-8")

    # Issue #43: a <select> fires "input" before "change". The shared
    # #filters input handler must not re-render on the Scan date select's
    # bubbled "input" event, or it clobbers the pick with the stale date
    # before the select's own dedicated "change" handler runs.
    filters_handler = script.split('byId("filters").addEventListener("input"', 1)[1]
    handler_body = filters_handler.split("});", 1)[0]
    assert 'event.target === byId("today-date")' in handler_body
    assert "return" in handler_body


def test_rubric_dialog_is_linkable_by_url_hash():
    script = Path("site/assets/app.js").read_text(encoding="utf-8")

    # Issue #41: opening the rubric must be shareable as a hashtag link, and
    # loading that link must reopen the same rubric version.
    assert "state.rubric" in script
    assert 'window.location.hash.slice(1)).get("rubric")' in script
    assert 'hashParams.set("rubric", state.rubric)' in script
    assert "openRubric(null, state.rubric)" in script


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

    assert "isAttention ? attentionActivity(item) : scoreBlock(item)" in script
    assert "openRubric(item)" not in script[script.index("function attentionActivity") :]


def test_detail_grid_shows_every_component_that_moves_the_total():
    script = Path("site/assets/app.js").read_text(encoding="utf-8")

    for component in ("Priority", "Relevance", "Evidence", "Recency", "Adoption"):
        assert f'["{component}", Number(item.' in script


def test_today_view_has_one_filterable_observation_list_and_one_source_status():
    html = Path("site/index.html").read_text(encoding="utf-8")
    script = Path("site/assets/app.js").read_text(encoding="utf-8")

    assert html.count("Matching observations") == 1
    assert 'id="today-list"' in html
    assert 'id="filters"' in html
    assert 'id="kind-filter"' in html
    assert "observations.map(observationCard)" in script
    assert "Daily field note" not in html
    assert "What entered the field?" not in html
    assert "today-overview" not in html
    assert "today-attention-list" not in html
    assert "Sources in results" not in script
    assert "health-summary" not in html


def test_summaries_truncate_at_a_word_boundary():
    script = Path("site/assets/app.js").read_text(encoding="utf-8")

    assert 'const lastSpace = candidate.lastIndexOf(" ");' in script
    assert "candidate.slice(0, lastSpace)" in script
    # The collapsed row is abbreviated, while the expanded region receives
    # the retained upstream text rather than the abbreviation.
    assert "shorten(item.summary)" in script
    assert 'text: item.summary || "No description published at the source."' in script


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


def test_main_filters_use_persisted_attention_and_snapshot_dates():
    script = Path("site/assets/app.js").read_text(encoding="utf-8")
    html = Path("site/index.html").read_text(encoding="utf-8")

    assert "loadExternalFeeds" not in script
    assert "state.external" not in script
    assert "day.attention.observations.map" in script
    assert "snapshot_date: day.date" in script
    assert 'id="kind-filter"' in html
    assert "renderExplorer" not in script
    assert "explorer-view" not in html


def test_records_expand_inline_without_an_exclusive_accordion_or_record_modal():
    script = Path("site/assets/app.js").read_text(encoding="utf-8")
    html = Path("site/index.html").read_text(encoding="utf-8")
    styles = Path("site/assets/styles.css").read_text(encoding="utf-8")

    assert '"details"' in script
    assert '"summary"' in script
    assert "record-detail" in script
    assert '.record-summary::before' in styles
    assert '.record-card[open] > .record-summary::before' in styles
    assert "detail-dialog" not in html
    assert "detail-dialog" not in script
    # A shared details[name] would force one row closed when another opens.
    assert "attrs: { name:" not in script
    assert script.count(".showModal()") == 1


def test_hugging_face_expansion_links_to_the_full_card():
    script = Path("site/assets/app.js").read_text(encoding="utf-8")

    assert 'item.source === "Hugging Face"' in script
    assert '"Read full card ↗"' in script


def test_trend_map_is_keyboard_accessible_and_coordinates_today_filters():
    html = Path("site/index.html").read_text(encoding="utf-8")
    script = Path("site/assets/app.js").read_text(encoding="utf-8")

    assert 'data-view="map"' in html
    assert 'id="map-canvas"' in html
    assert "state.data.corpus" in script
    assert "HAS_TOPIC" in script
    assert '"aria-label": `${entity.type}: ${entity.label}`' in script
    assert 'event.key === "Enter" || event.key === " "' in script
    assert "mapFilterFor(entity)" in script
    assert 'id="organization-filter"' in html
    assert "state.organization" in script


def test_trends_gate_comparisons_on_connector_coverage():
    script = Path("site/assets/app.js").read_text(encoding="utf-8")

    assert "sameCollectionContext" in script
    assert "coverage_signature" in script
    assert "Coverage is incomplete:" in script


def test_static_html_references_existing_local_assets():
    parser = SiteParser()
    parser.feed(Path("site/index.html").read_text(encoding="utf-8"))

    missing = []
    for reference in parser.local_refs:
        path = urlsplit(reference).path
        target = Path("site") if path in {"", ".", "./"} else Path("site") / path
        if not target.exists():
            missing.append(reference)

    assert not missing


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


def test_repo_badges_invite_an_action_rather_than_listing_a_roster():
    html = Path("site/index.html").read_text(encoding="utf-8")

    # Each badge sends the reader somewhere they can act. Linking to
    # /stargazers, /forks, or the issue list showed them a roster instead.
    assert 'href="https://github.com/ktwu01/benchmark-radar/fork"' in html
    assert 'href="https://github.com/ktwu01/benchmark-radar/issues/new"' in html
    assert 'href="https://github.com/ktwu01/benchmark-radar"' in html
    assert "/stargazers" not in html
    assert "benchmark-radar/forks" not in html

    for label in (">Star<", ">Fork<", ">Issues<"):
        assert label in html

    # Starring has no GET endpoint, so the star badge opens the repository and
    # the reader clicks Star there. Asserting the absence of a fabricated
    # /star URL keeps a future edit from inventing one that 404s.
    assert "benchmark-radar/star" not in html


def test_badge_accessible_names_state_the_action():
    script = Path("site/assets/app.js").read_text(encoding="utf-8")

    assert "BADGE_ACTIONS" in script
    for fragment in (
        "Star this repository on GitHub",
        "Fork this repository on GitHub",
        "Open a new issue on GitHub",
    ):
        assert fragment in script
    assert 'badge.setAttribute("aria-label"' in script
