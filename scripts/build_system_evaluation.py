#!/usr/bin/env python3
"""Build the comprehensive Benchmark Radar system and data evaluation."""

# ReportLab prose is intentionally kept as readable source text.
# ruff: noqa: E501

from __future__ import annotations

import argparse
from pathlib import Path

from build_technical_report import (
    AMBER,
    BLUE,
    BOLD,
    INK,
    ITALIC,
    MARGIN_X,
    MUTED,
    NAVY,
    PAGE_W,
    PALE_AMBER,
    PALE_TEAL,
    REGULAR,
    RULE,
    SKY,
    TEAL,
    WHITE,
    bullet,
    p,
    styles,
)
from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageBreak,
    PageTemplate,
    Spacer,
    Table,
    TableStyle,
)

GREEN = HexColor("#16794A")
PALE_GREEN = HexColor("#EAF7F0")
PURPLE = HexColor("#6D4AFF")


def table(rows: list[list], widths: list[float], *, tiny: bool = False) -> Table:
    pad = 4 if tiny else 5
    return Table(
        rows,
        colWidths=widths,
        repeatRows=1,
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, HexColor("#F8FAFC")]),
                ("GRID", (0, 0), (-1, -1), 0.42, RULE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), pad),
                ("RIGHTPADDING", (0, 0), (-1, -1), pad),
                ("TOPPADDING", (0, 0), (-1, -1), pad),
                ("BOTTOMPADDING", (0, 0), (-1, -1), pad),
            ]
        ),
    )


def metric_strip(st) -> Table:
    values = ["7,540", "4,537", "1,242", "37"]
    labels = [
        "source observations<br/>across 37 snapshots",
        "unique artifacts in the<br/>cumulative evidence graph",
        "searchable entries<br/>across 4 search sources",
        "public collection<br/>sources monitored",
    ]
    cells = [
        [p(value, st["metric"]), p(label, st["metric_label"])]
        for value, label in zip(values, labels, strict=True)
    ]
    return Table(
        [cells],
        colWidths=[1.65 * inch] * 4,
        rowHeights=[0.76 * inch],
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), SKY),
                ("BOX", (0, 0), (-1, -1), 0.7, BLUE),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, WHITE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        ),
    )


def search_surface(st) -> Table:
    input_box = Table(
        [
            [p("Search benchmarks, tasks, domains…", st["subtitle"])],
            [p("1,242 benchmarks  ·  4 sources", st["small"])],
        ],
        colWidths=[6.15 * inch],
        style=TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.8, HexColor("#AAB7C8")),
                ("LINEBELOW", (0, 0), (-1, 0), 0.4, RULE),
                ("BACKGROUND", (0, 0), (-1, -1), WHITE),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, 0), 6),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
                ("TOPPADDING", (0, 1), (-1, 1), 4),
                ("BOTTOMPADDING", (0, 1), (-1, 1), 6),
            ]
        ),
    )
    return Table(
        [[p("Search every benchmark", st["callout"])], [input_box]],
        colWidths=[6.6 * inch],
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), SKY),
                ("BOX", (0, 0), (-1, -1), 0.7, BLUE),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, 0), 8),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
                ("TOPPADDING", (0, 1), (-1, 1), 2),
                ("BOTTOMPADDING", (0, 1), (-1, 1), 9),
            ]
        ),
    )


def pipeline_figure() -> Drawing:
    drawing = Drawing(492, 101)
    boxes = [
        ("DISCOVER", "37 public sources"),
        ("VALIDATE", "health + schema"),
        ("RESOLVE", "exact IDs only"),
        ("INTERPRET", "taxonomy + rubric"),
        ("PUBLISH", "web, RSS, JSON"),
        ("QUERY", "offline CLI + HTTP"),
    ]
    box_w, gap = 72, 10
    for index, (title, caption) in enumerate(boxes):
        x = index * (box_w + gap)
        fill, stroke = (SKY, BLUE) if index % 2 == 0 else (PALE_TEAL, TEAL)
        drawing.add(
            Rect(x, 24, box_w, 51, 6, 6, fillColor=fill, strokeColor=stroke, strokeWidth=0.9)
        )
        drawing.add(
            String(
                x + box_w / 2,
                54,
                title,
                fontName=BOLD,
                fontSize=7.1,
                fillColor=NAVY,
                textAnchor="middle",
            )
        )
        drawing.add(
            String(
                x + box_w / 2,
                39,
                caption,
                fontName=REGULAR,
                fontSize=5.8,
                fillColor=MUTED,
                textAnchor="middle",
            )
        )
        if index < len(boxes) - 1:
            x1, x2 = x + box_w + 1, x + box_w + gap - 1
            drawing.add(Line(x1, 49, x2, 49, strokeColor=AMBER, strokeWidth=1.5))
            drawing.add(
                Polygon([x2, 49, x2 - 4, 52, x2 - 4, 46], fillColor=AMBER, strokeColor=AMBER)
            )
    drawing.add(
        String(
            246,
            6,
            "Snapshots remain canonical; derived products are rebuilt deterministically.",
            fontName=ITALIC,
            fontSize=6.9,
            fillColor=MUTED,
            textAnchor="middle",
        )
    )
    return drawing


def source_bars() -> Drawing:
    drawing = Drawing(492, 157)
    entries = [
        ("Hugging Face", 2452, BLUE),
        ("GitHub", 2008, TEAL),
        ("arXiv", 1482, AMBER),
        ("Semantic Scholar", 877, PURPLE),
        ("OpenAlex", 557, HexColor("#14919B")),
        ("Seven other labels", 164, HexColor("#94A3B8")),
    ]
    maximum, x0, width = 2600, 112, 315
    for index, (label, value, color) in enumerate(entries):
        y = 134 - index * 22
        drawing.add(String(0, y + 2.5, label, fontName=REGULAR, fontSize=7.5, fillColor=INK))
        drawing.add(Rect(x0, y, width, 9, 4, 4, fillColor=HexColor("#EFF3F8"), strokeColor=None))
        drawing.add(
            Rect(x0, y, width * value / maximum, 9, 4, 4, fillColor=color, strokeColor=None)
        )
        drawing.add(
            String(
                x0 + width + 8, y + 1.5, f"{value:,}", fontName=BOLD, fontSize=7.4, fillColor=INK
            )
        )
    drawing.add(
        String(
            x0,
            1,
            "7,540 cumulative source observations through 29 August 2026",
            fontName=ITALIC,
            fontSize=6.9,
            fillColor=MUTED,
        )
    )
    return drawing


class EvaluationDoc(BaseDocTemplate):
    def __init__(self, filename: str, *, doi: str):
        super().__init__(
            filename,
            pagesize=letter,
            rightMargin=MARGIN_X,
            leftMargin=MARGIN_X,
            topMargin=0.58 * inch,
            bottomMargin=0.58 * inch,
            title="Benchmark Radar: System and Data Evaluation",
            author="Koutian Wu",
            subject="Benchmark Radar technical report, version 1.0",
            keywords="AI benchmarks, evaluation, research software, data provenance, model cards",
        )
        self.doi = doi
        frame = Frame(
            self.leftMargin,
            self.bottomMargin,
            self.width,
            self.height,
            id="normal",
            leftPadding=0,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0,
        )
        self.addPageTemplates(PageTemplate(id="report", frames=[frame], onPage=self._page))

    def _page(self, canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.6)
        canvas.line(MARGIN_X, 0.40 * inch, PAGE_W - MARGIN_X, 0.40 * inch)
        canvas.setFont(REGULAR, 6.6)
        canvas.setFillColor(MUTED)
        canvas.drawString(
            MARGIN_X,
            0.22 * inch,
            f"Benchmark Radar System and Data Evaluation v1.0  |  DOI: {self.doi}",
        )
        canvas.drawRightString(PAGE_W - MARGIN_X, 0.22 * inch, str(doc.page))
        canvas.restoreState()


def story(doi: str) -> list:
    st = styles()
    tiny = ParagraphStyle("Tiny", parent=st["small"], fontSize=6.45, leading=8.0)
    story: list = []

    story.extend(
        [
            Spacer(1, 0.18 * inch),
            p(
                "TECHNICAL REPORT  |  SYSTEM AND DATA EVALUATION  |  VERSION 1.0",
                ParagraphStyle(
                    "Kicker",
                    parent=st["meta"],
                    fontName=BOLD,
                    fontSize=8.1,
                    textColor=BLUE,
                    spaceAfter=9,
                ),
            ),
            p("Benchmark Radar", st["title"]),
            p(
                "What the pipeline covers, what the numbers mean, and where its evidence stops",
                st["subtitle"],
            ),
            p("Koutian Wu", st["author"]),
            p(
                "29 August 2026  |  Software v0.9.0  |  Data cutoff 2026-08-29  |  Git 98c7de3",
                st["meta"],
            ),
            p(f"Reserved DOI: {doi}", st["meta"]),
            Spacer(1, 0.20 * inch),
            metric_strip(st),
            Spacer(1, 0.20 * inch),
            Table(
                [
                    [
                        p(
                            "The useful result is not one giant benchmark count. Benchmark Radar exposes four evidence layers, each answering a different question: what appeared today, what can be found in catalog search, what vendors report, and which score points are actually comparable.",
                            st["callout"],
                        )
                    ]
                ],
                colWidths=[6.6 * inch],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), PALE_AMBER),
                        ("BOX", (0, 0), (-1, -1), 0.8, AMBER),
                        ("LEFTPADDING", (0, 0), (-1, -1), 13),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 13),
                        ("TOPPADDING", (0, 0), (-1, -1), 10),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                    ]
                ),
            ),
            Spacer(1, 0.16 * inch),
            p("Executive findings", st["section"]),
            bullet(
                "<b>Coverage is broad but not a census.</b> The daily system monitors 37 public endpoints and the search surface reaches 1,242 entries, yet private, unindexed, deleted, and stale artifacts remain outside the observable frame.",
                st["body"],
            ),
            bullet(
                "<b>Provenance is the strongest part of the system.</b> 7,523 of 7,540 cumulative observations, or 99.77%, came from primary or structured sources; every published record keeps its source URL and retrieval metadata.",
                st["body"],
            ),
            bullet(
                "<b>The count contract must stay visible.</b> The 1,242-search total is 1,173 external catalog rows plus 69 curated score-tracked benchmarks. It is not the same population as 4,537 cumulative artifacts or 94 benchmarks in the adoption registry.",
                st["body"],
            ),
            bullet(
                "<b>The main gaps are measurable.</b> Four of 37 snapshots are simulated, only 41 of 4,537 artifacts have evidence from more than one normalized source, and all 4,129 KW-Bench tracks remain unclassified in this release.",
                st["body"],
            ),
            p("Abstract", st["subsection"]),
            p(
                "Benchmark Radar is a daily evidence-linked monitor, searchable benchmark catalog, model-card adoption registry, and protocol-aware score archive. This evaluation audits the README promises, collection and normalization pipeline, public reports, source coverage, query surfaces, and generated artifacts. It finds a well-tested, reproducible publication pipeline with explicit provenance guardrails, alongside limits in source availability, cross-source identity resolution, semantic retrieval, protocol completeness, and task-level classification. Counts are stated by unit so a discovery feed is not mistaken for the total benchmark market.",
                st["body"],
            ),
        ]
    )

    story.extend(
        [
            PageBreak(),
            p("1. What a reader can do", st["section"]),
            p(
                "The README leads with the user task: find a benchmark quickly, then inspect model-card adoption and score movement. The dashboard and RSS feed are the primary reading surfaces; JSON, the local CLI, and the local HTTP API are the reproducible research surfaces.",
                st["body"],
            ),
            search_surface(st),
            Spacer(1, 7),
            p("1.1 Why the search says 1,242 benchmarks · 4 sources", st["subsection"]),
            table(
                [
                    [
                        p("Search layer", st["table_header"]),
                        p("Rows", st["table_header"]),
                        p("Contribution", st["table_header"]),
                        p("Trust boundary", st["table_header"]),
                    ],
                    [
                        p("LLM Stats", st["small_bold"]),
                        p("687", st["small"]),
                        p("Names and 5,544 score rows.", st["small"]),
                        p("Aggregator scores lack full protocols.", st["small"]),
                    ],
                    [
                        p("OpenCompass Hub", st["small_bold"]),
                        p("461", st["small"]),
                        p("Paper, repo, publisher, release, dataset links.", st["small"]),
                        p("Identity leads; publisher may not be creator.", st["small"]),
                    ],
                    [
                        p("Artificial Analysis", st["small_bold"]),
                        p("25", st["small"]),
                        p("Current catalog and 7,050 score rows.", st["small"]),
                        p("Aggregator series stay outside curated scores.", st["small"]),
                    ],
                    [
                        p("Curated score tracks", st["small_bold"]),
                        p("69", st["small"]),
                        p("Benchmarks with cited score records.", st["small"]),
                        p("Instrument + protocol govern joins.", st["small"]),
                    ],
                    [
                        p("Displayed total", st["small_bold"]),
                        p("1,242", st["small_bold"]),
                        p("1,173 external + 69 curated rows.", st["small_bold"]),
                        p("Reach count, not a deduplicated census.", st["small_bold"]),
                    ],
                ],
                [1.35 * inch, 0.55 * inch, 2.25 * inch, 2.45 * inch],
            ),
            p(
                "The four sources beside the search box are search layers, not the 37 collection endpoints. External records stay one row per source, so a benchmark may appear more than once when equivalence has not been reviewed.",
                st["body"],
            ),
            p("1.2 Six usable surfaces", st["subsection"]),
            table(
                [
                    [
                        p("Surface", st["table_header"]),
                        p("Reader question", st["table_header"]),
                        p("Evaluation", st["table_header"]),
                    ],
                    [
                        p("Today", st["small_bold"]),
                        p("What appeared or changed?", st["small"]),
                        p("Ranked triage with evidence; not a quality verdict.", st["small"]),
                    ],
                    [
                        p("Search", st["small_bold"]),
                        p("Which records match this name, task, or domain?", st["small"]),
                        p("Transparent lexical matching; no semantic retrieval.", st["small"]),
                    ],
                    [
                        p("Leaderboard", st["small_bold"]),
                        p("Which benchmarks do labs report?", st["small"]),
                        p("Vendor attention, not benchmark quality.", st["small"]),
                    ],
                    [
                        p("Scores", st["small_bold"]),
                        p("Which printed values can be connected?", st["small"]),
                        p("Only identical instrument + protocol form a series.", st["small"]),
                    ],
                    [
                        p("Trends / map", st["small_bold"]),
                        p("Which topics and sources recur?", st["small"]),
                        p("Coverage signatures gate comparisons.", st["small"]),
                    ],
                    [
                        p("CLI + HTTP", st["small_bold"]),
                        p("Can an analyst reproduce search offline?", st["small"]),
                        p("One QueryService and stable JSON contract.", st["small"]),
                    ],
                ],
                [1.15 * inch, 2.65 * inch, 2.8 * inch],
            ),
        ]
    )

    story.extend(
        [
            PageBreak(),
            p("2. Pipeline evaluation", st["section"]),
            pipeline_figure(),
            p("2.1 Collection and health", st["subsection"]),
            p(
                "Each run queries enabled connectors inside a 48-hour window, records counts and errors, drops future-dated rows, then requires the configured core sources to be healthy. arXiv, Hugging Face, and GitHub are required. On the cutoff run all three were healthy; Semantic Scholar returned HTTP 429 and Brave had no API key; OpenReview was healthy but empty.",
                st["body"],
            ),
            p(
                "The cutoff run fetched 826 rows, deduplicated them to 783, classified 273 as eligible, and recommended 97. The published day merges two same-day collections and contains 528 records, 186 recommended. The report treats 528 as a daily published total, not as cumulative corpus size.",
                st["body"],
            ),
            p("2.2 Normalization, identity, and retention", st["subsection"]),
            bullet(
                "Stable fields include source ID, URL, title, timestamps, authors or organizations when supplied, parser version, retrieval time, and a SHA-256 payload fingerprint. Raw responses and credentials are not published.",
                st["body"],
            ),
            bullet(
                "Exact DOI, arXiv, OpenReview, GitHub, and Hugging Face anchors can merge observations. Title similarity alone cannot. This favors false splits over false joins.",
                st["body"],
            ),
            bullet(
                "Every taxonomy-matching, non-suppressed record is retained, including records below the recommendation threshold. Recommendation changes presentation, not corpus inclusion.",
                st["body"],
            ),
            p("2.3 Interpretation, publication, and query", st["subsection"]),
            p(
                "Priority combines relevance (35%), evidence (20%), recency (20%), and adoption (25%) on a 0–100 scale. Scoring version 5 is published with the data. Validated snapshots are canonical; generators replay them into the cumulative graph, normalize external catalogs, classify KW-Bench tracks, and package a checksummed release. Installed clients activate data atomically. Search never hides a failed update behind network fallback.",
                st["body"],
            ),
            table(
                [
                    [
                        p("Audit dimension", st["table_header"]),
                        p("What works", st["table_header"]),
                        p("Bound or risk", st["table_header"]),
                    ],
                    [
                        p("Reproducibility", st["small_bold"]),
                        p(
                            "Snapshots, schemas, parser versions, hashes, deterministic rebuilds.",
                            st["small"],
                        ),
                        p("Four early snapshots are simulated.", st["small"]),
                    ],
                    [
                        p("Reliability", st["small_bold"]),
                        p(
                            "Required-source gate; optional failures visible; atomic client activation.",
                            st["small"],
                        ),
                        p("Rate limits and secrets change realized coverage.", st["small"]),
                    ],
                    [
                        p("Identity", st["small_bold"]),
                        p("Exact-anchor merges and reviewed external groups.", st["small"]),
                        p("Only 41 artifacts have more than one source.", st["small"]),
                    ],
                    [
                        p("Interfaces", st["small_bold"]),
                        p("CLI and HTTP share QueryService and JSON.", st["small"]),
                        p("Search is lexical and local, not semantic or hosted.", st["small"]),
                    ],
                    [
                        p("Verification", st["small_bold"]),
                        p("Clean-worktree rebuild plus 1,028 passing tests.", st["small"]),
                        p("Tests do not establish source completeness.", st["small"]),
                    ],
                ],
                [1.15 * inch, 2.75 * inch, 2.70 * inch],
            ),
        ]
    )

    story.extend(
        [
            PageBreak(),
            p("3. Data products and counting contract", st["section"]),
            p(
                "The published populations overlap, but they are not interchangeable. A number should be cited with its unit and cutoff.",
                st["body"],
            ),
            table(
                [
                    [
                        p("Unit / product", st["table_header"]),
                        p("Count", st["table_header"]),
                        p("Definition", st["table_header"]),
                        p("Safe claim", st["table_header"]),
                    ],
                    [
                        p("Snapshot", st["small_bold"]),
                        p("37", st["small"]),
                        p("33 observed, 4 simulated.", st["small"]),
                        p("Available history, not independent samples.", st["small"]),
                    ],
                    [
                        p("Source observation", st["small_bold"]),
                        p("7,540", st["small"]),
                        p("Persisted source record.", st["small"]),
                        p("Evidence volume in cumulative replay.", st["small"]),
                    ],
                    [
                        p("Unique artifact", st["small_bold"]),
                        p("4,537", st["small"]),
                        p("Exact-ID-resolved paper, repo, dataset, release, or page.", st["small"]),
                        p("Distinct artifacts observed.", st["small"]),
                    ],
                    [
                        p("External catalog row", st["small_bold"]),
                        p("1,173", st["small"]),
                        p("One row from three catalog sources.", st["small"]),
                        p("Searchable records; duplicates may remain.", st["small"]),
                    ],
                    [
                        p("Searchable entry", st["small_bold"]),
                        p("1,242", st["small"]),
                        p("1,173 external + 69 curated score tracks.", st["small"]),
                        p("Current web-search reach.", st["small"]),
                    ],
                    [
                        p("Adoption benchmark", st["small_bold"]),
                        p("94", st["small"]),
                        p("Canonical identity in curated registry.", st["small"]),
                        p("Adoption denominator, including zero mentions.", st["small"]),
                    ],
                    [
                        p("Model-card document", st["small_bold"]),
                        p("36", st["small"]),
                        p("Curated reports from 11 organizations.", st["small"]),
                        p("Documents read for mentions.", st["small"]),
                    ],
                    [
                        p("Curated score", st["small_bold"]),
                        p("285", st["small"]),
                        p("Numeric result from a cited document; 69 tracks.", st["small"]),
                        p("Comparable only under exact protocols.", st["small"]),
                    ],
                    [
                        p("Model registry", st["small_bold"]),
                        p("861", st["small"]),
                        p("Models across curated and crawled layers; 19 in both.", st["small"]),
                        p("Inventory, not quality ranking.", st["small"]),
                    ],
                ],
                [1.30 * inch, 0.55 * inch, 2.45 * inch, 2.30 * inch],
                tiny=True,
            ),
            p("3.1 Cumulative source composition", st["subsection"]),
            source_bars(),
            p(
                "Five normalized source labels supply 7,376 of 7,540 observations (97.8%). Breadth across 37 endpoints does not mean equal contribution; it means multiple discovery routes whose realized yield and availability are reported separately.",
                st["body"],
            ),
            p("3.2 Adoption and score findings", st["subsection"]),
            p(
                "GPQA Diamond leads reporting breadth (26 of 36 documents, 10 organizations), followed by Humanity's Last Exam, SWE-bench Verified, Terminal-Bench, AIME, LiveCodeBench, MMLU-Pro, and BrowseComp. This is reporting convention, not superiority. The curated score layer identifies eight bounded metrics at or below five points of headroom and a reading gap where six benchmarks gained model-card mentions after their last readable score.",
                st["body"],
            ),
        ]
    )

    story.extend(
        [
            PageBreak(),
            p("4. Source inventory and health", st["section"]),
            p(
                "The README's 37 sources are 12 direct discovery connectors, 24 first-party feeds, and one public-attention source. The search box's four sources are a different concept.",
                st["body"],
            ),
            p("4.1 Direct discovery connectors (12)", st["subsection"]),
            table(
                [
                    [
                        p("Connector", st["table_header"]),
                        p("Role", st["table_header"]),
                        p("Cutoff run", st["table_header"]),
                        p("Core?", st["table_header"]),
                    ],
                    [
                        p("arXiv", tiny),
                        p("Primary papers via cs.AI/CL/CV/SE RSS", tiny),
                        p("Healthy · 23", tiny),
                        p("Yes", tiny),
                    ],
                    [
                        p("Hugging Face Hub", tiny),
                        p("Datasets and Spaces", tiny),
                        p("Healthy · 126", tiny),
                        p("Yes", tiny),
                    ],
                    [
                        p("GitHub Search", tiny),
                        p("Code and artifacts", tiny),
                        p("Healthy · 300; at cap", tiny),
                        p("Yes", tiny),
                    ],
                    [
                        p("GitHub Organizations", tiny),
                        p("Reviewed organization repos", tiny),
                        p("Healthy · 15", tiny),
                        p("No", tiny),
                    ],
                    [
                        p("Hugging Face Papers", tiny),
                        p("Community-surfaced papers", tiny),
                        p("Healthy · 23", tiny),
                        p("No", tiny),
                    ],
                    [
                        p("Kaggle Datasets", tiny),
                        p("Public benchmark datasets", tiny),
                        p("Healthy · 28", tiny),
                        p("No", tiny),
                    ],
                    [
                        p("Zenodo", tiny),
                        p("DOI-bearing artifacts", tiny),
                        p("Healthy · 77", tiny),
                        p("No", tiny),
                    ],
                    [
                        p("OpenReview", tiny),
                        p("Conference submissions", tiny),
                        p("Healthy · 0", tiny),
                        p("No", tiny),
                    ],
                    [
                        p("Semantic Scholar", tiny),
                        p("Structured scholarly discovery", tiny),
                        p("Failed · HTTP 429", tiny),
                        p("No", tiny),
                    ],
                    [
                        p("GitHub Releases", tiny),
                        p("Curated first-party releases", tiny),
                        p("Healthy · 3", tiny),
                        p("No", tiny),
                    ],
                    [
                        p("OpenAlex", tiny),
                        p("Scholarly discovery", tiny),
                        p("Healthy · 228", tiny),
                        p("No", tiny),
                    ],
                    [
                        p("Brave Search", tiny),
                        p("Web and official domains", tiny),
                        p("Unavailable · no key", tiny),
                        p("No", tiny),
                    ],
                ],
                [1.35 * inch, 2.45 * inch, 1.80 * inch, 0.70 * inch],
                tiny=True,
            ),
            p("4.2 First-party feeds (24)", st["subsection"]),
            table(
                [
                    [p("Feeds 1–12", st["table_header"]), p("Feeds 13–24", st["table_header"])],
                    [
                        p(
                            "Meituan Engineering<br/>OpenAI News<br/>Google AI<br/>Google DeepMind<br/>Google Research<br/>Apple Machine Learning Research<br/>AWS Machine Learning<br/>Hugging Face Blog<br/>Microsoft Research<br/>NVIDIA AI Blog<br/>Mistral AI<br/>Meta Research",
                            tiny,
                        ),
                        p(
                            "Ai2<br/>Together AI<br/>Sakana AI<br/>Qwen<br/>Ollama<br/>Stability AI<br/>Nomic AI<br/>Replicate<br/>NVIDIA Developer<br/>IBM Research<br/>Databricks<br/>LangChain",
                            tiny,
                        ),
                    ],
                ],
                [3.3 * inch, 3.3 * inch],
                tiny=True,
            ),
            p(
                "The feed collector was healthy and yielded three relevant records. A live feed can yield zero after relevance filtering without being broken. Organizations without a verified first-party feed are queried only through domain-constrained web searches; third-party mirrors are not substituted.",
                st["body"],
            ),
            p("4.3 Public attention (1)", st["subsection"]),
            p(
                "Hacker News is collected through its anonymous public API and rendered as unranked attention, separate from evidence. It yielded 12 records on the cutoff run and never contributes to quality or priority scores.",
                st["body"],
            ),
        ]
    )

    story.extend(
        [
            PageBreak(),
            p("5. Evidence quality and report audit", st["section"]),
            table(
                [
                    [
                        p("Finding", st["table_header"]),
                        p("Evidence", st["table_header"]),
                        p("Interpretation", st["table_header"]),
                    ],
                    [
                        p("High provenance", st["small_bold"]),
                        p("7,523 / 7,540 primary or structured (99.77%).", st["small"]),
                        p(
                            "Stable upstream records; not validation of every source claim.",
                            st["small"],
                        ),
                    ],
                    [
                        p("Low corroboration", st["small_bold"]),
                        p("41 / 4,537 artifacts have >1 normalized source (0.90%).", st["small"]),
                        p(
                            "Exact identity prevents bad joins but leaves plausible duplicates.",
                            st["small"],
                        ),
                    ],
                    [
                        p("Uneven yield", st["small_bold"]),
                        p("Five source labels provide 97.8% of observations.", st["small"]),
                        p("Caps or outages can change apparent topic mix.", st["small"]),
                    ],
                    [
                        p("Simulation", st["small_bold"]),
                        p("23–26 July are simulated snapshots.", st["small"]),
                        p("System-history test data, not observed market activity.", st["small"]),
                    ],
                    [
                        p("Classification gap", st["small_bold"]),
                        p("KW-Bench: 4,129 tracks, 0 classified.", st["small"]),
                        p(
                            "Task-capability view is scaffolding, not an empirical result.",
                            st["small"],
                        ),
                    ],
                    [
                        p("Protocol sparsity", st["small_bold"]),
                        p(
                            "12,594 aggregator scores stay outside curated progression.",
                            st["small"],
                        ),
                        p("Volume cannot replace missing evaluation conditions.", st["small"]),
                    ],
                    [
                        p("Lexical retrieval", st["small_bold"]),
                        p("Field tokens drive rank; no semantic reranker.", st["small"]),
                        p("Reproducible, but paraphrases can be missed.", st["small"]),
                    ],
                ],
                [1.45 * inch, 2.35 * inch, 2.80 * inch],
            ),
            p("5.1 Existing reports", st["subsection"]),
            table(
                [
                    [
                        p("Document", st["table_header"]),
                        p("Still useful for", st["table_header"]),
                        p("Do not reuse as", st["table_header"]),
                    ],
                    [
                        p("Landscape report, 31 Jul", st["small_bold"]),
                        p(
                            "A dated study of 791 sightings, 645 artifacts, and 78 agentic-evaluation artifacts.",
                            st["small"],
                        ),
                        p(
                            "A current market total; it predates most new sources and the external catalog.",
                            st["small"],
                        ),
                    ],
                    [
                        p("Source probes, 27 Aug", st["small_bold"]),
                        p("Verified HF Papers, Kaggle, Spaces, and Zenodo endpoints.", st["small"]),
                        p("A completeness or uptime guarantee.", st["small"]),
                    ],
                    [
                        p("External catalog audit", st["small_bold"]),
                        p(
                            "Why OpenCompass is identity-heavy and the other catalogs are score-heavy.",
                            st["small"],
                        ),
                        p(
                            "Permission to merge same-name benchmarks or protocol-free scores.",
                            st["small"],
                        ),
                    ],
                    [
                        p("Daily report / briefing", st["small_bold"]),
                        p("Triage with citations and source health.", st["small"]),
                        p("A literature review or neutral quality ranking.", st["small"]),
                    ],
                ],
                [1.65 * inch, 2.75 * inch, 2.20 * inch],
            ),
            p("5.2 Claims supported", st["subsection"]),
            bullet(
                "Supported: a source published or updated a record; it matched the declared taxonomy; a vendor document named a benchmark; a cited document printed a score under stored conditions.",
                st["body"],
            ),
            bullet(
                "Not supported by itself: the total benchmarks in existence; scientific benchmark quality; a fair model ranking across unlike protocols; proof that a benchmark is solved; or a field-wide trend when coverage changed.",
                st["body"],
            ),
        ]
    )

    story.extend(
        [
            PageBreak(),
            p("6. Decision-useful interpretation", st["section"]),
            p(
                "The strongest present-tense result is operational: Benchmark Radar turns a fragmented stream into traceable records that can be searched, filtered, downloaded, and re-queried offline. It also makes missing evidence visible.",
                st["body"],
            ),
            p("6.1 Vendor attention has converged on a small reporting core", st["subsection"]),
            p(
                "Eight benchmarks appear in documents from at least six organizations: GPQA Diamond, Humanity's Last Exam, SWE-bench Verified, Terminal-Bench, AIME, LiveCodeBench, MMLU-Pro, and BrowseComp. This is comparability of attention, not superiority. Repeated reporting can persist after a benchmark loses discriminatory power.",
                st["body"],
            ),
            p("6.2 Several bounded metrics are near their ceiling", st["subsection"]),
            p(
                "The curated layer records at most five points of headroom for AIME, Arena-Hard, DeepSearchQA, HMMT, MATH-500, MathVision, SWE-bench Verified, and tau2-bench. These are best-on-record observations, not proof of general saturation. Changing reasoning budget, tools, attempts, or evaluator can move a score without producing a comparable capability change.",
                st["body"],
            ),
            p("6.3 Breadth and evidence quality are intentionally asymmetric", st["subsection"]),
            p(
                "The 1,173-row external catalog is more than twelve times the 94-benchmark adoption registry. That breadth makes search useful for discovery; the curated registry supplies stronger attribution and protocol. The product should preserve this split: broad source-labelled search first, stronger claims only after review.",
                st["body"],
            ),
            p("6.4 Highest-value next measurements", st["subsection"]),
            table(
                [
                    [
                        p("Priority", st["table_header"]),
                        p("Measurement work", st["table_header"]),
                        p("Why it matters", st["table_header"]),
                    ],
                    [
                        p("1", st["small_bold"]),
                        p("Show the count unit beside every UI total and export.", st["small"]),
                        p("Prevents catalog reach from becoming a census claim.", st["small"]),
                    ],
                    [
                        p("2", st["small_bold"]),
                        p(
                            "Resolve high-value cross-source identities with anchors and review.",
                            st["small"],
                        ),
                        p("Raises corroboration without false families.", st["small"]),
                    ],
                    [
                        p("3", st["small_bold"]),
                        p("Complete KW-Bench extraction and reviewed coverage.", st["small"]),
                        p("Turns 4,129 unclassified tracks into a task map.", st["small"]),
                    ],
                    [
                        p("4", st["small_bold"]),
                        p("Expand protocol capture from newer model cards.", st["small"]),
                        p("Closes the mention-versus-score recency gap.", st["small"]),
                    ],
                    [
                        p("5", st["small_bold"]),
                        p(
                            "Add optional semantic retrieval while retaining lexical reasons.",
                            st["small"],
                        ),
                        p("Improves paraphrase recall without losing auditability.", st["small"]),
                    ],
                ],
                [0.55 * inch, 3.35 * inch, 2.70 * inch],
            ),
            Spacer(1, 10),
            Table(
                [
                    [
                        p("Bottom line", st["callout"]),
                        p(
                            "Benchmark Radar is ready to cite as an evidence-indexing system and open dataset. It should not be cited as a complete census, a benchmark-quality ranking, or a protocol-normalized model leaderboard.",
                            st["body"],
                        ),
                    ]
                ],
                colWidths=[1.1 * inch, 5.5 * inch],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), PALE_GREEN),
                        ("BOX", (0, 0), (-1, -1), 0.8, GREEN),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 10),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                        ("TOPPADDING", (0, 0), (-1, -1), 9),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                    ]
                ),
            ),
        ]
    )

    story.extend(
        [
            PageBreak(),
            p("7. Reproducibility, access, and citation", st["section"]),
            p(
                "This report evaluates Benchmark Radar v0.9.0 at Git commit 98c7de3 and data cutoff 2026-08-29. The clean worktree ran the CI sequence: lint and formatting checks, external normalization, KW-Bench classification, checksummed data-release construction, and the full test suite. All 1,028 tests passed.",
                st["body"],
            ),
            table(
                [
                    [
                        p("Artifact", st["table_header"]),
                        p("Canonical or permanent location", st["table_header"]),
                    ],
                    [
                        p("Technical report", st["small_bold"]),
                        p(f"https://doi.org/{doi}", st["small"]),
                    ],
                    [
                        p("Source code", st["small_bold"]),
                        p("https://github.com/ktwu01/benchmark-radar", st["small"]),
                    ],
                    [
                        p("Dashboard", st["small_bold"]),
                        p("https://benchmark-radar.org/", st["small"]),
                    ],
                    [
                        p("Cumulative JSON", st["small_bold"]),
                        p("https://benchmark-radar.org/data/radar.json", st["small"]),
                    ],
                    [
                        p("Benchmark catalog", st["small_bold"]),
                        p("https://benchmark-radar.org/data/benchmark-index.json", st["small"]),
                    ],
                    [
                        p("RSS", st["small_bold"]),
                        p("https://benchmark-radar.org/feed.xml", st["small"]),
                    ],
                    [
                        p("Citation metadata", st["small_bold"]),
                        p(
                            "https://github.com/ktwu01/benchmark-radar/blob/main/CITATION.cff",
                            st["small"],
                        ),
                    ],
                ],
                [1.55 * inch, 5.05 * inch],
            ),
            p("Suggested citation", st["subsection"]),
            p(
                f"Wu, K. (2026). <i>Benchmark Radar: System and Data Evaluation</i> (Technical Report v1.0). Zenodo. https://doi.org/{doi}",
                st["body"],
            ),
            p("Data statement", st["subsection"]),
            p(
                "Counts were recomputed from site/data/radar.json, site/data/benchmark-index.json, site/data/models.json, data/model_cards.yml, data/benchmark_scores.yml, normalized files under data/external/, and config.yml. The PDF is a dated interpretation. The rolling dashboard may change after the cutoff; cite its current number with a retrieval date.",
                st["body"],
            ),
            p("References", st["section"]),
            p(
                "[1] K. Wu. Benchmark Radar, version 0.9.0. GitHub, 2026. https://github.com/ktwu01/benchmark-radar",
                st["reference"],
            ),
            p(
                "[2] K. Wu. AI Benchmark Landscape Report. 2026. https://github.com/ktwu01/benchmark-radar/blob/main/docs/reports/ai-benchmark-landscape-report.md",
                st["reference"],
            ),
            p(
                "[3] K. Wu. Benchmark Radar cumulative corpus schema. 2026. https://github.com/ktwu01/benchmark-radar/blob/main/docs/cumulative-corpus.schema.json",
                st["reference"],
            ),
            p(
                "[4] K. Wu. Source probe evidence. 2026. https://github.com/ktwu01/benchmark-radar/blob/main/docs/source-probe-evidence.md",
                st["reference"],
            ),
            p(
                "[5] D. S. Katz et al. Recognizing the value of software: a software citation guide. F1000Research 9:1257, 2021. https://doi.org/10.12688/f1000research.26932.2",
                st["reference"],
            ),
            p(
                "[6] A. Smith, D. S. Katz, and K. E. Niemeyer. Software citation principles. PeerJ Computer Science 2:e86, 2016. https://doi.org/10.7717/peerj-cs.86",
                st["reference"],
            ),
            p(
                "[7] Citation File Format developers. Citation File Format 1.2.0. https://citation-file-format.github.io/",
                st["reference"],
            ),
            Spacer(1, 9),
            Table(
                [
                    [
                        p(
                            "Repository: github.com/ktwu01/benchmark-radar<br/>Dashboard: benchmark-radar.org<br/>Software license: MIT  |  Report license: CC BY 4.0",
                            ParagraphStyle(
                                "EndCard",
                                parent=st["body"],
                                fontName=BOLD,
                                fontSize=8.6,
                                leading=12.5,
                                textColor=NAVY,
                            ),
                        )
                    ]
                ],
                colWidths=[6.6 * inch],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), SKY),
                        ("BOX", (0, 0), (-1, -1), 0.7, BLUE),
                        ("TOPPADDING", (0, 0), (-1, -1), 9),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                    ]
                ),
            ),
        ]
    )
    return story


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", type=Path, default=Path("output/pdf/benchmark-radar-technical-report-v1.0.pdf")
    )
    parser.add_argument("--doi", default="10.5281/zenodo.22167102")
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    EvaluationDoc(str(args.output), doi=args.doi).build(story(args.doi))
    print(args.output)


if __name__ == "__main__":
    main()
