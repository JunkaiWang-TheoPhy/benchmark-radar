from datetime import UTC, datetime
from urllib.error import HTTPError

from benchmark_radar.sources import fetch_arxiv, fetch_github

ARXIV_XML = """\
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2607.12345v2</id>
    <updated>2026-07-26T18:00:00Z</updated>
    <published>2026-07-23T18:00:00Z</published>
    <title>Weekend benchmark</title>
    <summary>A benchmark announced after the submission window.</summary>
    <author><name>Radar Author</name></author>
  </entry>
</feed>
"""

ARXIV_RSS = """\
<rss xmlns:arxiv="http://arxiv.org/schemas/atom"
     xmlns:dc="http://purl.org/dc/elements/1.1/" version="2.0">
  <channel>
    <item>
      <title>Fallback evaluation benchmark</title>
      <link>https://arxiv.org/abs/2607.54321</link>
      <description>arXiv:2607.54321v1 Announce Type: new
Abstract: A benchmark recovered from the official category feed.</description>
      <guid isPermaLink="false">oai:arXiv.org:2607.54321v1</guid>
      <pubDate>Mon, 27 Jul 2026 00:00:00 -0400</pubDate>
      <arxiv:announce_type>new</arxiv:announce_type>
      <dc:creator>Radar Author, Second Author</dc:creator>
    </item>
  </channel>
</rss>
"""


def test_arxiv_uses_overlap_and_updated_timestamp(monkeypatch):
    calls = []
    delays = []
    monkeypatch.setattr(
        "benchmark_radar.sources.get_text",
        lambda url, params: calls.append(params) or ARXIV_XML,
    )
    monkeypatch.setattr("benchmark_radar.sources.time.sleep", delays.append)
    since = datetime(2026, 7, 25, 12, tzinfo=UTC)

    items = fetch_arxiv(
        {
            "queries": ["one", "two", "three"],
            "overlap_hours": 120,
            "request_delay_seconds": 3,
        },
        since,
        10,
    )

    assert len(calls) == 3
    assert delays == [3, 3]
    assert len(items) == 1
    assert items[0].published_at == datetime(2026, 7, 23, 18, tzinfo=UTC)
    assert items[0].updated_at == datetime(2026, 7, 26, 18, tzinfo=UTC)
    assert items[0].event_kind == "updated"


def test_arxiv_falls_back_to_official_rss_when_atom_is_rate_limited(monkeypatch):
    def fake_get_text(url, params=None):
        if url == "https://export.arxiv.org/api/query":
            raise HTTPError(url, 429, "Too Many Requests", {}, None)
        assert url == "https://rss.arxiv.org/rss/cs.AI"
        return ARXIV_RSS

    monkeypatch.setattr("benchmark_radar.sources.get_text", fake_get_text)

    items = fetch_arxiv(
        {
            "queries": ["all:benchmark"],
            "rss_categories": ["cs.AI"],
            "rss_keywords": ["benchmark"],
        },
        datetime(2026, 7, 25, 12, tzinfo=UTC),
        10,
    )

    assert len(items) == 1
    assert items[0].source_id == "2607.54321"
    assert items[0].published_at == datetime(2026, 7, 27, 4, tzinfo=UTC)
    assert items[0].authors == ["Radar Author", "Second Author"]
    assert items[0].event_kind == "released"


def test_arxiv_can_use_official_rss_as_primary(monkeypatch):
    def fake_get_text(url, params=None):
        assert url == "https://rss.arxiv.org/rss/cs.AI"
        assert params is None
        return ARXIV_RSS

    monkeypatch.setattr("benchmark_radar.sources.get_text", fake_get_text)

    items = fetch_arxiv(
        {
            "atom_enabled": False,
            "queries": ["must not be requested"],
            "rss_categories": ["cs.AI"],
            "rss_keywords": ["benchmark"],
        },
        datetime(2026, 7, 25, 12, tzinfo=UTC),
        10,
    )

    assert [item.source_id for item in items] == ["2607.54321"]


def _github_row(index: int) -> dict:
    return {
        "full_name": f"org/repo{index}",
        "html_url": f"https://github.com/org/repo{index}",
        "pushed_at": "2026-07-27T00:00:00Z",
        "created_at": "2026-07-27T00:00:00Z",
        "description": f"Benchmark suite {index}",
        "stargazers_count": index,
        "forks_count": 0,
    }


def test_github_pages_past_the_hundred_row_search_limit(monkeypatch):
    # The search API caps a response at 100 rows, so a single request silently
    # dropped everything beyond it whenever a query matched more.
    monkeypatch.setattr("benchmark_radar.sources.time.sleep", lambda seconds: None)
    requested_pages = []

    def fake_get_json(url, params=None, headers=None):
        requested_pages.append(params["page"])
        start = (params["page"] - 1) * 100
        if start >= 150:
            return {"items": []}
        return {"items": [_github_row(start + offset) for offset in range(min(100, 150 - start))]}

    monkeypatch.setattr("benchmark_radar.sources.get_json", fake_get_json)

    items = fetch_github(
        {"queries": ["benchmark"]},
        datetime(2026, 7, 25, 12, tzinfo=UTC),
        300,
    )

    assert requested_pages == [1, 2]
    assert len(items) == 150


def test_github_stops_paging_once_a_page_is_short(monkeypatch):
    monkeypatch.setattr("benchmark_radar.sources.time.sleep", lambda seconds: None)
    calls = []

    def fake_get_json(url, params=None, headers=None):
        calls.append(params["page"])
        return {"items": [_github_row(0)]}

    monkeypatch.setattr("benchmark_radar.sources.get_json", fake_get_json)

    items = fetch_github(
        {"queries": ["benchmark"]},
        datetime(2026, 7, 25, 12, tzinfo=UTC),
        300,
    )

    assert calls == [1]
    assert len(items) == 1


def test_github_bounds_total_requests_when_unauthenticated(monkeypatch):
    # Search allows ~10 requests/minute without a token. Paging every query to
    # exhaustion tripped a 403, which fails a required source and aborts the run.
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr("benchmark_radar.sources.time.sleep", lambda seconds: None)
    calls = []

    def fake_get_json(url, params=None, headers=None):
        calls.append(params["page"])
        # Rows repeat across queries, so the per-source limit is never reached
        # and only the request budget can stop the walk.
        return {"items": [_github_row(offset) for offset in range(100)]}

    monkeypatch.setattr("benchmark_radar.sources.get_json", fake_get_json)

    fetch_github(
        {"queries": ["a", "b", "c", "d"], "max_requests": 8},
        datetime(2026, 7, 25, 12, tzinfo=UTC),
        1000,
    )

    assert len(calls) == 8


def test_github_spaces_unauthenticated_requests(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    delays = []
    monkeypatch.setattr("benchmark_radar.sources.time.sleep", delays.append)
    monkeypatch.setattr(
        "benchmark_radar.sources.get_json",
        lambda url, params=None, headers=None: {
            "items": [_github_row(offset) for offset in range(100)]
        },
    )

    fetch_github(
        {"queries": ["a"], "max_requests": 3},
        datetime(2026, 7, 25, 12, tzinfo=UTC),
        300,
    )

    assert delays and all(delay > 0 for delay in delays)


def test_github_pages_round_robin_so_no_query_is_skipped(monkeypatch):
    # Draining the first query to the source limit spent the whole budget on
    # it and never issued the other configured searches, dropping whole topics.
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr("benchmark_radar.sources.time.sleep", lambda seconds: None)
    queried = []

    def fake_get_json(url, params=None, headers=None):
        queried.append(params["q"].split(" pushed")[0])
        return {"items": [_github_row(offset) for offset in range(100)]}

    monkeypatch.setattr("benchmark_radar.sources.get_json", fake_get_json)

    fetch_github(
        {"queries": ["alpha", "beta", "gamma"], "max_requests": 3},
        datetime(2026, 7, 25, 12, tzinfo=UTC),
        300,
    )

    assert sorted(queried) == ["alpha", "beta", "gamma"]
