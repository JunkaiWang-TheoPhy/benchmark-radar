import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from generate_star_history import cumulative_points, render_svg  # noqa: E402


def test_cumulative_points_groups_stars_by_day():
    assert cumulative_points([date(2026, 8, 2), date(2026, 8, 1), date(2026, 8, 2)]) == [
        (date(2026, 8, 1), 1),
        (date(2026, 8, 2), 3),
    ]


def test_render_svg_is_theme_aware_and_escapes_repository_name():
    points = [(date(2026, 8, 1), 1), (date(2026, 8, 3), 4)]

    light = render_svg("owner/repo&chart", points, dark=False)
    dark = render_svg("owner/repo&chart", points, dark=True)

    assert "owner/repo&amp;chart Star History" in light
    assert "4 stars · 2026-08-01 – 2026-08-03" in light
    assert 'fill="#ffffff"' in light
    assert 'fill="#0d1117"' in dark
    assert "<path" in light


def test_render_svg_handles_an_empty_repository():
    svg = render_svg("owner/repo", [], dark=False)

    assert "No stars yet" in svg
    assert "0 stars" in svg
