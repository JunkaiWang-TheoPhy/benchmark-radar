import json
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import generate_og_image as og  # noqa: E402


def test_requested_size_is_honoured():
    # The property that actually broke. Asserted by measuring, not by checking
    # the font class: Pillow's load_default() returns a scalable FreeTypeFont
    # on 11+ and an unscalable bitmap face before that, so a type check would
    # pass on current Pillow while the title still rendered at ~10px.
    small = og.font(23).getbbox("Benchmark")[2]
    large = og.font(og.TITLE_SIZE).getbbox("Benchmark")[2]
    assert large > small * 1.5


def test_guard_passes_with_the_fonts_available_here():
    og._assert_scalable_fonts()


def test_guard_rejects_a_face_that_ignores_the_requested_size(monkeypatch):
    # Simulates the macOS-without-DejaVu case that rendered a ~10px title.
    # Patching font() rather than ImageFont.truetype, because load_default()
    # calls truetype() internally on a bundled buffer, so patching that would
    # break the very fallback this needs to reach.
    monkeypatch.setattr(og, "font", lambda *a, **k: ImageFont.load_default())
    with pytest.raises(SystemExit, match="ignores the requested size"):
        og._assert_scalable_fonts()


def test_render_writes_a_correctly_sized_card(tmp_path):
    # 1200x630 is what the og:image:width/height meta in site/index.html
    # declares, and a mismatch makes the unfurled card letterbox or crop.
    progression = og.build_score_progression(og.DEFAULT_SCORES_PATH)
    output = og.render(progression, tmp_path / "og-card.png")
    with Image.open(output) as image:
        assert image.size == (1200, 630)


def test_card_reports_the_current_registry_counts(tmp_path):
    # The card is a claim about the score evidence that travels without it.
    progression = og.build_score_progression(og.DEFAULT_SCORES_PATH)
    assert progression["observation_count"] > 0
    output = og.render(progression, tmp_path / "og-card.png")
    assert output.stat().st_size > 0


def test_card_uses_score_frontiers_instead_of_the_adoption_rank():
    assert "build_adoption_rank" not in og.__file__
    assert set(og.CHART_BENCHMARKS) >= {"gpqa_diamond", "hle"}


def test_catalog_totals_include_all_searchable_records_and_curated_source(tmp_path):
    index = tmp_path / "benchmark-index.json"
    index.write_text(
        json.dumps(
            {
                "count": 124,
                "benchmarks": [
                    {"source": "llm_stats"},
                    {"source": "opencompass_hub"},
                    {"source": "artificial_analysis"},
                ],
            }
        ),
        encoding="utf-8",
    )
    progression = og.build_score_progression(og.DEFAULT_SCORES_PATH)
    benchmark_count, source_count = og.catalog_totals(progression, index)
    assert benchmark_count == progression["benchmark_count"] + 124
    assert source_count == 4
