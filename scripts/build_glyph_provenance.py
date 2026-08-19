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
    # xAI ships one identity, and it is Grok's: the company has no separate
    # corporate mark in use, so the organization and the model family are the
    # same brand and now draw the same licensed glyph. The bold X that stood
    # here was drawn in this repo for want of anything better.
    "ORGANIZATION_ICONS[xAI]": LOBE.format("grok"),
    # No set publishes a usable mark for Z.ai, so its Z wordmark is drawn in
    # this repo. Recorded as PLACEHOLDER rather than pinned to an upstream:
    # the point of this file is that a hand-authored path is declared as one,
    # not that it is forbidden. What was forbidden, and what shipped anyway,
    # was a hand-authored path presenting itself as a real brand mark (Meta,
    # issue #261).
    "ORGANIZATION_ICONS[Z.ai]": PLACEHOLDER,
    # Issue #266: the organizations that had been drawing the generic spark.
    # All from Lobe Icons, which carries AI-company marks simple-icons does
    # not. Two are the mark that set publishes for the company rather than a
    # literal company wordmark, and both were kept deliberately: microsoft.svg
    # is titled "Azure", and Meituan's is `longcat`, its model brand.
    # AI21 and IBM were briefly dropped for #267 and are back. Judged again in
    # the real chart context -- a 14px glyph inside its circle, in the
    # organization's color, rather than as black type on white -- AI21's four
    # bold glyphs read cleanly and IBM's striped block stays recognizable.
    # IBM ships no symbol at any size because the striped lettering IS its
    # mark, so dropping it traded a legible wordmark for no mark at all.
    "ORGANIZATION_ICONS[AI21 Labs]": LOBE.format("ai21"),
    "ORGANIZATION_ICONS[Ai2]": LOBE.format("ai2"),
    "ORGANIZATION_ICONS[Amazon]": LOBE.format("aws"),
    "ORGANIZATION_ICONS[Baidu]": LOBE.format("baidu"),
    "ORGANIZATION_ICONS[ByteDance]": LOBE.format("bytedance"),
    "ORGANIZATION_ICONS[Cohere]": LOBE.format("cohere"),
    "ORGANIZATION_ICONS[IBM]": LOBE.format("ibm"),
    "ORGANIZATION_ICONS[Inception]": LOBE.format("inception"),
    "ORGANIZATION_ICONS[LG AI Research]": LOBE.format("lg"),
    "ORGANIZATION_ICONS[Liquid AI]": LOBE.format("liquid"),
    "ORGANIZATION_ICONS[Meituan]": LOBE.format("longcat"),
    "ORGANIZATION_ICONS[Microsoft]": LOBE.format("microsoft"),
    "ORGANIZATION_ICONS[MiniMax]": LOBE.format("minimax"),
    "ORGANIZATION_ICONS[NVIDIA]": LOBE.format("nvidia"),
    "ORGANIZATION_ICONS[Nous Research]": LOBE.format("nousresearch"),
    "ORGANIZATION_ICONS[StepFun]": LOBE.format("stepfun"),
    "ORGANIZATION_ICONS[Tencent]": LOBE.format("tencent"),
    "ORGANIZATION_ICONS[Upstage]": LOBE.format("upstage"),
    # Issue #267: `xiaomimimo` is two stacked lines of type, and a chart point
    # draws its glyph at roughly 14px, where that collapses into a smudge.
    # simple-icons ships the MI symbol, which survives the size. The company
    # mark rather than the model brand, same trade as Microsoft/Azure above.
    "ORGANIZATION_ICONS[Xiaomi]": SIMPLE_ICONS.format("xiaomi"),
    "MODEL_FAMILY_ICONS[Claude]": LOBE.format("claude"),
    "MODEL_FAMILY_ICONS[Gemini]": LOBE.format("gemini"),
    "MODEL_FAMILY_ICONS[Grok]": LOBE.format("grok"),
}


def tables() -> dict[str, list[str]]:
    text = GLYPHS.read_text(encoding="utf-8")
    found: dict[str, list[str]] = {}
    for table in ("ORGANIZATION_ICONS", "MODEL_FAMILY_ICONS"):
        block = text.split(f"const {table} = {{", 1)[1].split("\n};", 1)[0]
        for match in re.finditer(r'\n  ("?[\w. ]+"?): \[\s*\n((?:\s*"[^"]+",\n)+)\s*\]', block):
            found[f"{table}[{match.group(1).strip(chr(34))}]"] = re.findall(
                r'"([^"]+)"', match.group(2)
            )
    return found


def upstream_paths(url: str) -> list[str]:
    """Every path in the upstream mark, in document order.

    Several marks are legitimately multi-path -- Azure's four squares,
    Upstage's eleven strokes -- and `iconGlyph` already appends one <path> per
    entry, so nothing needed to change to draw them. What is rejected is a mark
    that cannot render as a flat monochrome glyph at all: every path is filled
    with currentColor, so a gradient, mask or clip-path would silently lose its
    shape rather than fail. Poolside's mark is exactly that, and it stays on
    the generic spark instead of shipping broken.
    """
    with urllib.request.urlopen(url) as response:
        svg = response.read().decode("utf-8")
    for unsupported in ("<mask", "linearGradient", "radialGradient", "clip-path="):
        if unsupported in svg:
            raise SystemExit(f"{url}: carries {unsupported}, cannot render as a flat glyph")
    paths = re.findall(r'<path[^>]*\sd="([^"]+)"', svg)
    if not paths:
        raise SystemExit(f"{url}: no paths found")
    return paths


def digest(paths: list[str]) -> str:
    """One digest over every path, so a dropped or reordered path is caught."""
    return hashlib.sha256("\u0000".join(paths).encode("utf-8")).hexdigest()


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
            marks[key] = {"url": PLACEHOLDER, "sha256": digest(committed)}
            continue
        real = upstream_paths(url)
        if real != committed:
            mismatched.append(f"  {key}\n    committed differs from {url}")
        marks[key] = {"url": url, "sha256": digest(real)}

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
