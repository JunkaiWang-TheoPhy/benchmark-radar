"""Build human-readable descriptions from source metadata.

The radar must never present a templated sentence as if it were a description.
Boilerplate is worse than an empty string for two reasons:

1. It tells the reader nothing that the source and event chips do not already say.
2. `score_item` reads `summary`, so a template that contains taxonomy words
   ("dataset", "benchmark") makes the pipeline score itself on its own prose and
   inflates relevance for every record from that source.

So every helper here returns text drawn from the upstream payload, or "" when the
upstream genuinely published nothing. Callers must treat "" as "no description
available" rather than substituting a filler sentence.
"""

from __future__ import annotations

import re
from typing import Any

# Card text arrives as rendered markdown: tabs, collapsed headings, badge alt
# text. Keep the first real sentence(s) and drop the scaffolding.
_WHITESPACE = re.compile(r"\s+")
# Images first: a badge is often an image wrapped in a link, and removing the
# inner image leaves the outer link matchable rather than a stray "](url)".
_MARKDOWN_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_MARKDOWN_NOISE = re.compile(
    r"""
    \[([^\]]*)\]\([^)]*\)   # links: keep the visible label, drop the target
    | <[^>]+>               # inline html
    | ^\s*[#>*-]+\s*        # heading / quote / bullet markers
    | [*_`]{1,3}            # emphasis and code ticks
    """,
    re.VERBOSE | re.MULTILINE,
)
# YAML front matter in a dataset card is metadata, not description prose.
_FRONT_MATTER = re.compile(r"\A\s*---.*?\n---\s*", re.DOTALL)

# Keep enough upstream prose for useful inline expansion while bounding the
# static payload. The UI links to the full source/card for anything beyond it.
MAX_SUMMARY_CHARS = 2_000


def clean_card_text(text: str | None) -> str:
    """Reduce a dataset/model card to plain prose, or "" if nothing survives."""
    if not text:
        return ""
    stripped = _FRONT_MATTER.sub("", text)
    stripped = _MARKDOWN_IMAGE.sub(" ", stripped)
    # Link labels are real prose, so keep group 1; other alternatives have no
    # group and collapse to a space.
    stripped = _MARKDOWN_NOISE.sub(lambda match: match.group(1) or " ", stripped)
    collapsed = _WHITESPACE.sub(" ", stripped).strip()
    if len(collapsed) <= MAX_SUMMARY_CHARS:
        return collapsed
    # Prefer a sentence boundary so the text does not end mid-word.
    window = collapsed[: MAX_SUMMARY_CHARS + 1]
    cut = max(window.rfind(". "), window.rfind("! "), window.rfind("? "))
    if cut > MAX_SUMMARY_CHARS // 3:
        return window[: cut + 1].strip()
    return collapsed[:MAX_SUMMARY_CHARS].rsplit(" ", 1)[0].strip() + "…"


def _echoes_title(text: str, title: str) -> bool:
    """True when the card opens by repeating its own repo name and says no more."""
    slug = title.rsplit("/", 1)[-1]
    normalize = lambda value: re.sub(r"[^a-z0-9]+", "", value.lower())  # noqa: E731
    return normalize(text) == normalize(slug)


def strip_title_echo(text: str, title: str) -> str:
    """Drop a leading repeat of the repo name, which carries no new information."""
    if not text:
        return ""
    slug = title.rsplit("/", 1)[-1]
    pattern = re.compile(rf"\A{re.escape(slug)}\s*[:.\-–]?\s*", re.IGNORECASE)
    trimmed = pattern.sub("", text).strip()
    return "" if _echoes_title(trimmed, title) or not trimmed else trimmed


def huggingface_summary(row: dict[str, Any], title: str) -> str:
    """Describe a Hugging Face repo using only what its maintainer published.

    Returns "" when the repo has no card and no descriptive tags, which is itself
    a signal: an unlabelled repo is usually a scratch upload, not a release.
    """
    prose = strip_title_echo(clean_card_text(row.get("description")), title)
    if prose:
        return prose
    # No card. Fall back to curator-authored metadata, which is still real
    # evidence, unlike a generated sentence.
    card = row.get("cardData") or {}
    facets: list[str] = []
    tasks = card.get("task_categories") or card.get("task_ids") or []
    if isinstance(tasks, list) and tasks:
        facets.append("tasks: " + ", ".join(str(value) for value in tasks[:3]))
    sizes = card.get("size_categories")
    if sizes:
        size = sizes[0] if isinstance(sizes, list) and sizes else sizes
        facets.append(f"size: {size}")
    languages = card.get("language") or []
    if isinstance(languages, list) and languages:
        facets.append("language: " + ", ".join(str(value) for value in languages[:3]))
    # Author-supplied tags exclude the machine-generated `license:`/`region:`
    # namespaces that every repo carries.
    free_tags = [
        tag
        for tag in (row.get("tags") or [])
        if isinstance(tag, str) and ":" not in tag and tag.lower() not in {"benchmark", "dataset"}
    ]
    if free_tags:
        facets.append("tagged: " + ", ".join(free_tags[:4]))
    return "No dataset card. Declared " + "; ".join(facets) + "." if facets else ""


def github_summary(row: dict[str, Any]) -> str:
    """GitHub repo description, or "" when the owner left it blank."""
    return clean_card_text(row.get("description"))
