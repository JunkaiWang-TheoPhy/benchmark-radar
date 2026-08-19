"""Pin every brand mark to the upstream file it came from.

Issue #261: Meta's committed path was byte-identical to simple-icons for 395
characters and invented for the next 1,200. Same subpath count, same command
mix, every coordinate inside the viewBox -- no static heuristic separates a
fabricated brand path from a real one, and it rendered as a blob for a year
without failing anything.

What does separate them is the file each path claims to come from. This script
fetches those files and records a digest of the exact path bytes, so the test
suite can assert "nobody edited a brand mark by hand" offline, on every run.

Run when a mark is deliberately added or changed, which should be rare:

    python scripts/build_glyph_provenance.py
"""

from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from pathlib import Path

GLYPHS = Path("site/assets/glyphs.js")
OUTPUT = Path("site/assets/glyph-provenance.json")

SIMPLE_ICONS = "https://raw.githubusercontent.com/simple-icons/simple-icons/master/icons/{}.svg"
LOBE = "https://raw.githubusercontent.com/lobehub/lobe-icons/master/packages/static-svg/icons/{}.svg"

# A mark drawn in this repo because no licensed upstream one exists.
PLACEHOLDER = "placeholder:hand-drawn-in-repo"

# Which upstream file each table entry claims to be. simple-icons is the
# default set; OpenAI is absent from it (OpenAI restricts its mark), so that
# one and the model-family marks come from Lobe Icons, MIT licensed.
SOURCES = {
    "ORGANIZATION_ICONS[Anthropic]": SIMPLE_ICONS.format("anthropic"),
    "ORGANIZATION_ICONS[DeepSeek]": SIMPLE_ICONS.format("deepseek"),
    "ORGANIZATION_ICONS[Google]": SIMPLE_ICONS.format("google"),
    "ORGANIZATION_ICONS[Meta]": SIMPLE_ICONS.format("meta"),
    "ORGANIZATION_ICONS[Mistral]": SIMPLE_ICONS.format("mistralai"),
    "ORGANIZATION_ICONS[Moonshot AI]": SIMPLE_ICONS.format("moonshotai"),
    "ORGANIZATION_ICONS[OpenAI]": LOBE.format("openai"),
    "ORGANIZATION_ICONS[Qwen]": SIMPLE_ICONS.format("qwen"),
    # Neither set publishes a usable mark for these two, so both are drawn in
    # this repo -- a bold X for xAI, the Z wordmark for Z.ai. Recorded as
    # PLACEHOLDER rather than pinned to an upstream: the point of this file is
    # that a hand-authored path is declared as one, not that it is forbidden.
    # What was forbidden, and what shipped anyway, was a hand-authored path
    # presenting itself as a real brand mark (Meta, issue #261).
    "ORGANIZATION_ICONS[Z.ai]": PLACEHOLDER,
    "ORGANIZATION_ICONS[xAI]": PLACEHOLDER,
    "MODEL_FAMILY_ICONS[Claude]": LOBE.format("claude"),
    "MODEL_FAMILY_ICONS[Gemini]": LOBE.format("gemini"),
    "MODEL_FAMILY_ICONS[Grok]": LOBE.format("grok"),
}


def tables() -> dict[str, str]:
    text = GLYPHS.read_text(encoding="utf-8")
    found: dict[str, str] = {}
    for table in ("ORGANIZATION_ICONS", "MODEL_FAMILY_ICONS"):
        block = text.split(f"const {table} = {{", 1)[1].split("\n};", 1)[0]
        for match in re.finditer(r'\n  ("?[\w. ]+"?): \[\s*\n?\s*"([^"]+)",?\s*\n?\s*\]', block):
            found[f"{table}[{match.group(1).strip(chr(34))}]"] = match.group(2)
    return found


def upstream_path(url: str) -> str:
    with urllib.request.urlopen(url) as response:
        svg = response.read().decode("utf-8")
    paths = re.findall(r'<path[^>]*\sd="([^"]+)"', svg)
    if len(paths) != 1:
        raise SystemExit(f"{url}: expected one path, found {len(paths)}")
    return paths[0]


def main() -> None:
    marks: dict[str, dict[str, str]] = {}
    mismatched: list[str] = []

    for key, committed in sorted(tables().items()):
        url = SOURCES.get(key)
        if url is None:
            raise SystemExit(
                f"{key} has no upstream source recorded. Add it to SOURCES, or "
                f"the mark cannot be verified and should not ship."
            )
        if url == PLACEHOLDER:
            marks[key] = {
                "url": PLACEHOLDER,
                "sha256": hashlib.sha256(committed.encode("utf-8")).hexdigest(),
            }
            continue
        real = upstream_path(url)
        if real != committed:
            mismatched.append(f"  {key}\n    committed differs from {url}")
        marks[key] = {
            "url": url,
            "sha256": hashlib.sha256(real.encode("utf-8")).hexdigest(),
        }

    if mismatched:
        raise SystemExit(
            "These committed paths do not match upstream:\n"
            + "\n".join(mismatched)
            + "\n\nFix the path in glyphs.js rather than recording the digest of a\n"
            "hand-edited mark -- that is exactly the failure this file prevents."
        )

    OUTPUT.write_text(
        json.dumps(
            {
                "note": (
                    "Digests of the upstream brand paths committed in glyphs.js. "
                    "Rebuild with scripts/build_glyph_provenance.py; never edit by hand."
                ),
                "marks": marks,
            },
            indent=2,
        )
        + "\n"
    )
    print(f"verified {len(marks)} marks against upstream -> {OUTPUT}")


if __name__ == "__main__":
    main()
