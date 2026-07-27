from datetime import UTC, datetime

from benchmark_radar.sources import fetch_arxiv

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
