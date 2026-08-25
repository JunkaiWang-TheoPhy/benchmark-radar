"""Reshape the Artificial Analysis crawl into the snapshot registry's format.

The crawl arrived as three normalized tables joined by id: evaluations, models,
and scores. Every other snapshot in `data/leaderboard_snapshots.yml` is two
denormalized CSVs with the llm-stats header vocabulary, and the loader and the
normalizer both read that vocabulary. A third shape would mean a second loader,
a second normalizer and a second set of invariants to keep in step, so the
crawl is reshaped to fit the registry rather than the registry widened to fit
the crawl.

WHAT THE RESHAPE HAS TO DECIDE

Two things do not survive a straight copy.

The scores table carries ids only. Model name and organization live in the
models table, and the registry format wants them on the row, so they are joined
in here once instead of being looked up at every read.

One evaluation can publish more than one number. GDPval-AA v2 reports a raw Elo
around 1,000 to 1,800 and a normalized score between 0 and 1 for the same 213
models, which is two rows per (evaluation, model) where the registry allows
one. They are not one series: they are two measurements on different scales, so
they become two benchmark rows. That is also what stops a chart drawing them on
one axis, where the normalized half would collapse onto the baseline.

Evaluations publishing a single number keep their own id unchanged, so the
split shows up only where the source actually published a second number.

WHAT IS DROPPED, AND WHY THAT IS NOT A LOSS

`normalized_value_0_100` is not carried into `normalized_score`. That column
means "fraction of the declared maximum" in the llm-stats vocabulary, on a 0 to
1 scale; the source's own normalization is a different claim on a different
scale, and two meanings in one column is the confusion this reshape exists to
avoid. Where the source published a normalized number as its own metric, it
survives as that metric's own benchmark row with its value intact.

Confidence intervals, the methodology version and the source's grouping of its
own runs have no column in the registry format. The registry records what an
aggregator reported, with its crawl timestamp and source URL, and deliberately
records no protocol: `comparable_group` is null for every crawled row, and a
version string carried alongside it would read as the protocol the layer says
it does not have.

WHERE THE INPUT WENT

This ran once against the three tables committed in 836188e, and its two output
CSVs are now the snapshot of record. The three input tables were then removed
from the tree: keeping both would store the same crawl twice, in two shapes,
with nothing certifying that they still say the same thing, which is the
duplication this reshape exists to end. They remain in history, so recovering
them to rerun this is `git show 836188e`.

A future Artificial Analysis crawl is handled the same way: land the raw
tables, run this, commit the two CSVs, drop the raw.

    python scripts/reshape_artificial_analysis.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

SOURCE_DIR = Path("data/leaderboard_snapshots/artificial_analysis_2026-08-25")
OUT_DIR = Path("data/leaderboard_snapshots")

EVALUATIONS = SOURCE_DIR / "artificial_analysis_evaluations_2026-08-25.csv"
MODELS = SOURCE_DIR / "artificial_analysis_models_2026-08-25.csv"
SCORES = SOURCE_DIR / "artificial_analysis_scores_2026-08-25.csv"
MANIFEST = SOURCE_DIR / "artificial_analysis_manifest_2026-08-25.json"

BENCHMARKS_OUT = OUT_DIR / "artificial_analysis_benchmarks_2026-08-25.csv"
SCORES_OUT = OUT_DIR / "artificial_analysis_benchmark_scores_2026-08-25.csv"

# The llm-stats vocabulary, because that is what the loader and the normalizer
# read. Columns the source cannot fill are written empty rather than omitted, so
# the two snapshots have the same header and a reader diffing them sees a blank
# where a value is genuinely absent.
BENCHMARK_HEADER = (
    "benchmark_id",
    "name",
    "description",
    "categories",
    "modality",
    "max_score",
    "detail_source_url",
)
SCORE_HEADER = (
    "benchmark_id",
    "benchmark_name",
    "rank",
    "model_id",
    "model_name",
    "organization_name",
    "benchmark_score",
    "self_reported",
    "announcement_date",
    "source_url",
)

# How a split component is named for a reader. The component slug is the
# source's own field name, which is precise but not a label.
COMPONENT_LABELS = {
    "raw_elo": "Elo",
    "normalized_score": "normalized score",
}


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [{k: (v or "") for k, v in row.items()} for row in csv.DictReader(handle)]


def main() -> None:
    evaluations = _read(EVALUATIONS)
    models = {row["source_model_id"].strip(): row for row in _read(MODELS)}
    scores = _read(SCORES)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    # Certify the crawl against the counts it shipped with before reshaping it,
    # so a truncated input fails here rather than producing a short snapshot
    # that the registry then certifies as complete against its own declaration.
    if len(evaluations) != manifest["required_evaluation_count"]:
        raise SystemExit(
            f"evaluations: {len(evaluations)} vs manifest {manifest['required_evaluation_count']}"
        )
    if len(models) != manifest["captured_model_count"]:
        raise SystemExit(f"models: {len(models)} vs manifest {manifest['captured_model_count']}")
    if len(scores) != manifest["score_row_count"]:
        raise SystemExit(f"scores: {len(scores)} vs manifest {manifest['score_row_count']}")

    components: dict[str, set[str]] = {}
    for row in scores:
        components.setdefault(row["source_evaluation_id"].strip(), set()).add(
            row["metric_component"].strip()
        )

    def benchmark_id(evaluation_id: str, component: str) -> str:
        if len(components.get(evaluation_id, ())) < 2:
            return evaluation_id
        return f"{evaluation_id}:{component}"

    def benchmark_name(evaluation_id: str, name: str, component: str) -> str:
        if len(components.get(evaluation_id, ())) < 2:
            return name
        return f"{name} ({COMPONENT_LABELS.get(component, component)})"

    benchmark_rows: list[dict[str, str]] = []
    for evaluation in sorted(evaluations, key=lambda r: r["source_evaluation_id"].strip()):
        evaluation_id = evaluation["source_evaluation_id"].strip()
        for component in sorted(components.get(evaluation_id, {""})):
            benchmark_rows.append(
                {
                    "benchmark_id": benchmark_id(evaluation_id, component),
                    "name": benchmark_name(evaluation_id, evaluation["name"].strip(), component),
                    "description": evaluation["description"].strip(),
                    "categories": evaluation["ui_categories_json"].strip(),
                    # The source publishes no modality field and no ceiling. An
                    # empty cell is the answer, not a gap to be filled later.
                    "modality": "",
                    "max_score": "",
                    "detail_source_url": evaluation["detail_url"].strip(),
                }
            )

    names = {row["source_evaluation_id"].strip(): row["name"].strip() for row in evaluations}
    score_rows: list[dict[str, str]] = []
    for row in scores:
        evaluation_id = row["source_evaluation_id"].strip()
        component = row["metric_component"].strip()
        model = models[row["source_model_id"].strip()]
        score_rows.append(
            {
                "benchmark_id": benchmark_id(evaluation_id, component),
                "benchmark_name": benchmark_name(evaluation_id, names[evaluation_id], component),
                "rank": row["source_rank"].strip(),
                "model_id": row["source_model_id"].strip(),
                "model_name": model["name"].strip(),
                "organization_name": model["creator_name"].strip(),
                "benchmark_score": row["raw_value"].strip(),
                # Artificial Analysis runs the evaluation itself, so no row here
                # is a vendor's claim about its own model.
                "self_reported": "False",
                # The model's own release date. The source records no evaluation
                # date on any row, and the normalizer labels this for what it is.
                "announcement_date": row["model_release_date"].strip(),
                "source_url": row["source_url"].strip(),
            }
        )

    # Sorted so a rerun against the same crawl is byte-identical.
    score_rows.sort(key=lambda r: (r["benchmark_id"], int(r["rank"] or 0), r["model_id"]))

    pairs = {(r["benchmark_id"], r["model_id"]) for r in score_rows}
    if len(pairs) != len(score_rows):
        raise SystemExit("reshape left duplicate (benchmark_id, model_id) rows")

    for path, header, rows in (
        (BENCHMARKS_OUT, BENCHMARK_HEADER, benchmark_rows),
        (SCORES_OUT, SCORE_HEADER, score_rows),
    ):
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(header), lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        print(f"{len(rows)} rows -> {path}")


if __name__ == "__main__":
    main()
