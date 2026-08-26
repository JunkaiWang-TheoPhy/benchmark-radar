from pathlib import Path

# Strict scan: any remaining "基准" in user-facing sources is suspicious.  # allow-基准
# Keep this broad but exlude generated / snapshot data and third-party fixtures.
STRICT_EXCLUDE_DIRS = {
    "data/snapshots",
    "data/leaderboard_snapshots",
    "site/data",
    ".git",
    "__pycache__",
    ".venv",
    "node_modules",
}
STRICT_EXCLUDE_FILES = {
    # Historical fixtures kept for snapshot tests; not user-facing copy.
    "tests/fixtures/daily_briefing_zh.json",
}


def test_chinese_translations_use_benchmark_not_ji_zhun() -> None:
    """Regression for #374: zh strings should use 'benchmark' instead of '基准'."""  # allow-基准
    text = Path("site/assets/app.js").read_text(encoding="utf-8")
    # Simple check: no occurrence of 基准 should remain in user-facing JS.  # allow-基准
    assert "基准" not in text, (  # allow-基准
        "site/assets/app.js still contains '基准'; "  # allow-基准
        "use 'benchmark' in zh strings (see #374)"  # allow-基准
    )


def test_no_ji_zhun_in_user_facing_sources_strict() -> None:
    """Broad regression for #374: any '基准' in user-facing copy is suspicious.  # allow-基准

    This check is intentionally strict and may be wrong (false positive).  # allow-基准
    If a hit is legitimate (e.g. a proper noun, quoted external text, or
    non-user-facing comment), either rephrase to 'benchmark' or add the
    file to STRICT_EXCLUDE_FILES with a comment explaining why, then
    re-run CI. See #374.
    """
    root = Path(__file__).parents[1]
    hits: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if any(rel.startswith(d) for d in STRICT_EXCLUDE_DIRS):
            continue
        if rel in STRICT_EXCLUDE_FILES:
            continue
        if path.suffix not in {".js", ".ts", ".yml", ".yaml", ".md", ".py", ".json"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        if "基准" in text:  # allow-基准
            # Allow explicit opt-out per line: "# allow-基准" / "<!-- allow-基准 -->"
            lines = []
            for i, line in enumerate(text.splitlines(), 1):
                if "基准" in line and "allow-基准" not in line:  # allow-基准
                    lines.append(f"  {rel}:{i}: {line.strip()[:120]}")
            if lines:
                hits.extend(lines)

    assert not hits, (  # allow-基准
        "Found '基准' in user-facing sources (strict check, may be wrong — "  # allow-基准
        "see test header). Prefer 'benchmark' in zh copy per #374, or add "  # allow-基准
        "an allowlist entry with justification.\n" + "\n".join(hits)  # allow-基准
    )
