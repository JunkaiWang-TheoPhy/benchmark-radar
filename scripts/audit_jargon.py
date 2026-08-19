"""Find project vocabulary that leaked into user-facing text.

Issue #241 asks that the site read to a 16-year-old. The failure it names is
specific and recurring: a word that is precise inside this codebase gets
printed to a reader who has never seen the codebase. "Comparable run" meant
a group of scores sharing an instrument and a protocol, which is exactly
right internally and meaningless on a chart (issue #261).

This scans the strings a reader actually sees -- the i18n keys in app.js and
the copy in the HTML -- and reports the terms below. It is deliberately a
small hand-written list rather than a readability score: Flesch-Kincaid
rewards short words, and "run", "row" and "shard" are short. The problem is
unexplained vocabulary, not long sentences.

    python scripts/audit_jargon.py            # human-readable
    python scripts/audit_jargon.py --markdown # issue body
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# term -> why a reader outside this project cannot be expected to know it.
JARGON = {
    "comparable run": "internal name for scores sharing an instrument and protocol",
    "comparable group": "internal join key; means nothing to a reader",
    "instrument": "used here to mean the exact test variant, not its dictionary sense",
    "protocol": "used here to mean the run conditions, not its dictionary sense",
    "shard": "storage detail; a reader does not load files",
    "corpus": "means 'everything collected'; say that instead",
    "donor": "internal term for a record lending its identity",
    "connector": "internal name for a data source adapter",
    "provenance": "means 'where this came from'; say that instead",
    "normalization": "pipeline step; invisible to a reader",
    "schema": "developer word for the shape of a file",
    "observation count": "means 'how many scores'; say that instead",
    "saturation": "jargon unless the page explains it on the spot",
    "frontier": "used here as a section name, not a plain-English word",
    "readable score": "project term of art; explained on some pages, not all",
}

# Text a reader sees. Comments and code identifiers are exempt: naming a
# concept precisely in source is the point, and only printed strings are read.
I18N_KEY = re.compile(r'^\s*"([^"]{4,})":\s*"', re.M)
HTML_TEXT = re.compile(r">([^<>{}]{12,})<", re.S)


# An i18n key is English prose; a lookup key like "frontier.explainer.sub" or a
# DOM attribute like "data-frontier-point" is not, and flagging those would
# bury the real hits under noise the reader never sees.
NOT_PROSE = re.compile(r"^[a-z0-9_.-]+$|^data-|^aria-")


def user_facing_strings(root: Path) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    app = root / "site/assets/app.js"
    if app.exists():
        # The i18n table's keys are the English the site prints.
        for m in I18N_KEY.finditer(app.read_text(encoding="utf-8")):
            key = m.group(1)
            if not NOT_PROSE.match(key) and " " in key:
                out.append((str(app.relative_to(root)), key))
    for html in sorted((root / "site").glob("*.html")):
        for m in HTML_TEXT.finditer(html.read_text(encoding="utf-8")):
            text = " ".join(m.group(1).split())
            if text and not text.startswith(("//", "/*")):
                out.append((str(html.relative_to(root)), text))
    return out


def findings(root: Path) -> list[tuple[str, str, str, str]]:
    hits = []
    for where, text in user_facing_strings(root):
        low = text.lower()
        for term, why in JARGON.items():
            if re.search(rf"\b{re.escape(term)}s?\b", low):
                hits.append((term, where, text, why))
    hits.sort(key=lambda h: (h[0], h[1]))
    return hits


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--markdown", action="store_true")
    ap.add_argument("--root", type=Path, default=Path("."))
    args = ap.parse_args()
    hits = findings(args.root)

    if args.markdown:
        print("## Jargon in user-facing text\n")
        if not hits:
            print("No flagged terms this week. Nothing to do.")
            return 0
        print(
            f"{len(hits)} place(s) print a word that only makes sense inside this "
            "project. Each line is the text a reader sees.\n"
        )
        current = None
        for term, where, text, why in hits:
            if term != current:
                current = term
                print(f"\n### `{term}`\n\n_{why}_\n")
            snippet = text if len(text) <= 160 else text[:157] + "..."
            print(f"- `{where}` — {snippet}")
        print(
            "\n---\nNot every hit is a bug: a term the surrounding sentence "
            "defines is fine. Rewrite the ones that assume the reader already "
            "knows. Refs #241."
        )
    else:
        for term, where, text, _ in hits:
            print(f"{term}\t{where}\t{text[:90]}")
        print(f"\n{len(hits)} hit(s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
