from datetime import UTC, datetime

from benchmark_radar.models import RadarItem, RadarRun, SourceHealth
from benchmark_radar.report import render_markdown


def test_report_contains_evidence_and_health():
    record = RadarItem(
        source="GitHub",
        source_id="org/repo",
        title="Benchmark | Suite",
        url="https://github.com/org/repo",
        published_at=datetime(2026, 7, 27, tzinfo=UTC),
        categories=["benchmark"],
        total_score=3.1,
        evidence_score=2,
        relevance_score=3,
        recency_score=4,
        rationale=["Primary source: GitHub"],
    )
    report = render_markdown(
        RadarRun(
            generated_at=datetime(2026, 7, 27, tzinfo=UTC),
            since=datetime(2026, 7, 25, tzinfo=UTC),
            items=[record],
            health=[SourceHealth(source="github", ok=True, item_count=1)],
        )
    )
    assert "Benchmark \\| Suite" in report
    assert "Primary source" in report
    assert "Source health" in report
