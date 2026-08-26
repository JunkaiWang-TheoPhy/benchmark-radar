from pathlib import Path


def test_chinese_translations_use_benchmark_not_ji_zhun() -> None:
    """Regression for #374: zh strings should use 'benchmark' instead of '基准'."""
    text = Path("site/assets/app.js").read_text(encoding="utf-8")
    # Simple check: no occurrence of 基准 should remain in user-facing JS.
    assert "基准" not in text, (
        "site/assets/app.js still contains '基准'; use 'benchmark' in zh strings (see #374)"
    )
