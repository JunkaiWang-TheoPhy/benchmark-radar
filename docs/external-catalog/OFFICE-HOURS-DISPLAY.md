# What we should really display

Office hours, 2026-08-18. Rewritten after actually opening the page instead of reasoning
about it. Two of my earlier conclusions were wrong and are corrected here.

## Correction 1: the saturation panel already exists, and it is good

`?view=leaderboard&lfrontier=gpqa_diamond` renders a three-band chart:

- **Top band, largest:** cumulative distinct organizations, a staircase. Adoption.
- **Middle:** a rug of model-card ticks.
- **Bottom band, small, labelled ACCURACY (ZOOMED):** the score track. This is saturation.

Underneath it: best on record 94.3%, headroom left 5.7, readable values 20 across 13
dates and 2 comparable runs. Then a **PAIRED COMPARISON ONLY** box that states in plain
words what the data supports ("two dates share an instrument and protocol, so the pair is
a like-for-like before-and-after") and what it does not ("a direction over time; two
points define one segment, a third would be needed before the word trend applies").

I proposed building an honest saturation scatter. It is already built, and its honesty
discipline is stricter than what I proposed. Nothing about the chart needs inventing.

## Correction 2: the selector is not capped at 13

`#adoption-frontier` contains a `<select>` labelled ALL TRACKED BENCHMARKS carrying **all
79** registry benchmarks, verified in a browser. Issue #240 says "at most ~13 benchmarks
are ever selectable" and an earlier version of `AUDIT.md` repeated it after I checked the
`.slice()` and not the markup beside it. Both were wrong. Every registry benchmark is
already reachable.

The real gap is that 79 is 7% of the roughly 1,066 distinct benchmarks the crawls cover,
and no crawled record appears in that select at all.

## What the merge actually does: it inverts the panel

This is the design consequence, and it is not mentioned in #240.

The panel today leads with adoption and treats score as the small band underneath. The
title is "GPQA DIAMOND **ADOPTION TRAJECTORY**". That is built for a reader studying
reporting convention, which is what Benchmark Radar has always been about.

For the 1,148 crawled records:

| band | canonical benchmark | crawled-only benchmark |
|---|---|---|
| cumulative organizations | works | **impossible**, no model cards exist |
| model-card rug | works | **impossible** |
| score track | 20 readable values (GPQA Diamond) | **239** reported values (GPQA, llm-stats) |

So merging does not add a row to an existing chart. It produces a second, different
panel: one band instead of three, and that one band an order of magnitude denser than the
curated equivalent. 5,544 crawled scores against 70 curated observations.

The panel has to work in two modes, and the crawled mode is the **simpler** one.

## The real problem, stated from the reader's moment

A researcher arrives with a name because someone in lab meeting said "include MMLU." They
have about five seconds and one question: is this still worth running in 2026?

Today the page answers a different question first, in a bigger font, with two paragraphs
of preamble above it. Adoption is the headline; saturation is a zoomed strip near the
bottom. For the reader we named, the emphasis is inverted.

That is a copy and hierarchy problem, not a data problem, and it does not require the
merge to fix.

## What to change

**Reorder, do not rebuild.** The score band moves above the adoption band for benchmarks
that have both, and the headline stops saying "adoption trajectory" when the reader came
for saturation. The PAIRED COMPARISON ONLY box stays exactly as written; it is the best
piece of honesty writing in the codebase.

**Crawled-only benchmarks render the one-band version.** Score track, n, source label,
the mixed-protocol caveat, licence, publisher. No adoption staircase, no headroom figure
(headroom needs a trustworthy bound and the crawled layer has none: `vending-bench-2`
declares max 1.0 and carries 8017.59).

**Feed the crawled points into the existing score band, kept visually distinct.** GPQA
goes from 20 curated points to 259. The curated points keep their protocol-checked
connections; the crawled points are scatter only and never join a line, because
`comparable_group` is null on all 5,544 of them.

**The x-axis for crawled points is model release date, not evaluation date.** 5,522 of
5,544 rows carry it; zero carry an evaluation date. That distinction has to be in the
axis label, not a footnote, because "when the model came out" and "when it was scored"
are different claims.

**Keep the thin-year problem visible.** MMLU reads 2023: 0.86, 2024: 0.92, 2025: 0.93,
2026: 0.91 with n=5 in 2026. It did not get harder; strong labs stopped reporting it. Any
rendering that lets that read as decline is a lie the existing panel already guards
against with its gap-marking rule. The same rule has to survive the merge.

## What I would remove

The stage-grouped shortlist as primary navigation. Not because 13 is too few, that was my
error, but because a shortlist and a 79-option select and a search box in one panel is
three navigation systems for one job. Search subsumes both once it covers 1,148.

## The assignment

Open `?view=leaderboard&lfrontier=mmlu` and read the panel as if you had five seconds and
came from lab meeting. Note where your eye lands first and whether it answers "is this
still worth running". Then decide whether the fix is reordering the bands or rewriting the
headline. That judgement is yours and it does not need any more data work to make.
