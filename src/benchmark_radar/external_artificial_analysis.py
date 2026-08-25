"""Artificial Analysis: 24 evaluations, 618 models, 7,050 scores, normalized.

The third aggregator source, and the first that runs its own evaluations rather
than restating what vendors report. That difference is what this module has to
preserve, because it changes what the numbers mean.

WHY THIS SOURCE DOES NOT GO THROUGH `leaderboard_snapshots.yml`

That registry's loader certifies one shape: a catalog CSV, and a scores CSV
whose rows are one per (benchmark, model), carrying the benchmark name, the
model name and the organization inline. The Artificial Analysis export is three
normalized tables, not two denormalized ones. Its scores file carries ids only
and joins to a separate models file, and one (evaluation, model) pair can hold
more than one row because an evaluation can publish more than one metric
component: GDPval-AA v2 reports both a raw Elo and a source-published
normalized score for the same 213 models.

Flattening that to fit the registry would mean either dropping one of the two
GDPval components or duplicating 618 model names across 7,050 rows. The first
loses data the source published, the second invents a second copy of the model
table that can drift from the first. So this source is read here directly, the
way `external_opencompass.py` reads its own round 2 export, and the registry
keeps its narrower contract intact.

WHY ONE SERIES PER EVALUATION, WITH COMPONENTS INSIDE IT

A shard holds one series per record key, so 24 evaluations produce 24 series.
The metric components are not collapsed into that: each series lists its
components with their own counts and observed ranges, and every observation
names the component it belongs to. A reader can still separate GDPval's Elo
from its normalized score, and no consumer has to guess that two numbers on one
model are two different measurements.

WHAT IS COPIED THROUGH RATHER THAN INTERPRETED

The source's own grouping is carried as `source_comparable_group`, and
`comparable_group` stays null like every other crawled row. Artificial Analysis
really does state a protocol version, so its rows genuinely are comparable to
each other, and throwing that away would lose something true. But
`comparable_group` is the curated layer's field, and it means "these may be
drawn on one line". Writing an aggregator's self-declared group into it would
let a crawled row join a document's series, which is the flattening this
codebase exists to refuse. Two different claims, two different field names.

`normalized_value_0_100` is kept beside `raw_value`, never in place of it, with
the source's `normalization_basis` sentence attached. 278 rows have a raw value
and no normalization; those stay null rather than being normalized here, since
inventing the missing scale is exactly the guess this layer exists not to make.

`evaluated_at` is empty on all 7,050 rows, so `reported_date` carries the
model's release date under `date_precision: model_announcement`, the same
labelled substitute `external_catalog.py` uses and for the same reason.

WHAT THE IDENTITY FILE IS ALLOWED TO DO

Nothing, yet. All 24 shipped mappings are `needs_review` with a null canonical
id, and this module refuses any mapping that names a canonical benchmark
without two independent anchors. The snapshot must not move a model-card
adoption count on the strength of a name match.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import yaml

from .external_catalog import (
    CATALOG_SCHEMA_VERSION,
    DEFAULT_OUTPUT_DIR,
    ExternalCatalogError,
    assign_slugs,
    canonical_organization,
    finite_float,
    json_list,
    value_kind,
)

ARTIFICIAL_ANALYSIS_SOURCE = "artificial_analysis"
ARTIFICIAL_ANALYSIS_KEY_PREFIX = "artificial-analysis"

DEFAULT_SNAPSHOT_DIR = Path("data/leaderboard_snapshots/artificial_analysis_2026-08-25")

_EVALUATIONS_FILE = "artificial_analysis_evaluations_2026-08-25.csv"
_MODELS_FILE = "artificial_analysis_models_2026-08-25.csv"
_SCORES_FILE = "artificial_analysis_scores_2026-08-25.csv"
_MANIFEST_FILE = "artificial_analysis_manifest_2026-08-25.json"
_IDENTITY_FILE = "artificial_analysis_identity_candidates_2026-08-25.yml"

# Anything less is a name match, and a name match is not an identity. The
# shipped file asserts no canonical ids at all; this is the gate a later
# hand-promoted mapping has to pass.
_REQUIRED_IDENTITY_ANCHORS = 2


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise ExternalCatalogError(f"{path}: Artificial Analysis snapshot file not found")
    with path.open(newline="", encoding="utf-8") as handle:
        rows = [
            {key: (value or "") for key, value in row.items()} for row in csv.DictReader(handle)
        ]
    if not rows:
        raise ExternalCatalogError(f"{path}: no data rows")
    return rows


def _require_columns(rows: list[dict[str, str]], columns: tuple[str, ...], *, path: Path) -> None:
    """Fail on a renamed upstream header here, not on empty fields downstream."""
    missing = [column for column in columns if column not in rows[0]]
    if missing:
        raise ExternalCatalogError(f"{path}: missing columns: {', '.join(sorted(missing))}")


def _source_record(row: dict[str, str], slug: str) -> dict[str, Any]:
    source_id = row["source_evaluation_id"].strip()
    description = row.get("description", "").strip()
    return {
        "key": f"{ARTIFICIAL_ANALYSIS_KEY_PREFIX}:{source_id}",
        "slug": slug,
        "schema_version": CATALOG_SCHEMA_VERSION,
        "source": ARTIFICIAL_ANALYSIS_SOURCE,
        "source_benchmark_id": source_id,
        "name": row.get("name", "").strip() or source_id,
        "description": {"en": description} if description else {},
        # The source publishes evaluation pages, not benchmark provenance: no
        # author, no paper, no repository, no dataset size. Empty is the answer.
        "publisher": None,
        "artifacts": [],
        "openness": {
            "status": "unknown",
            "code_license": None,
            "data_license": None,
            "evidence": [],
        },
        "sizes": [],
        "released": None,
        "modality": None,
        "categories": json_list(row.get("ui_categories_json", "")),
        "provenance": {
            "source_url": row.get("detail_url", "").strip() or None,
            "crawled_at": row.get("crawled_at", "").strip() or None,
            "crawl_bundle": None,
        },
    }


def _observation(row: dict[str, str], model: dict[str, str], *, key: str) -> dict[str, Any]:
    evaluation_id = row["source_evaluation_id"].strip()
    model_id = row["source_model_id"].strip()
    component = row["metric_component"].strip()
    raw_value = row.get("raw_value", "").strip()
    parsed = finite_float(raw_value)
    rank = row.get("source_rank", "").strip()
    return {
        # The component is part of the identity: GDPval-AA v2 publishes two
        # numbers for one model, and they are two observations, not a conflict.
        "obs_id": f"{ARTIFICIAL_ANALYSIS_SOURCE}:{evaluation_id}:{model_id}:{component}",
        "key": key,
        "series_id": f"{ARTIFICIAL_ANALYSIS_SOURCE}:{evaluation_id}:default",
        "metric_component": component,
        "model_name": model.get("name", "").strip(),
        "model_id": model_id,
        "organization": canonical_organization(model.get("creator_name")),
        "raw_value": raw_value,
        "value": parsed,
        "value_kind": value_kind(raw_value, parsed),
        "display_value": row.get("display_value", "").strip() or None,
        "normalized_value_0_100": finite_float(row.get("normalized_value_0_100", "")),
        "normalization_basis": row.get("normalization_basis", "").strip() or None,
        "unit": row.get("unit", "").strip() or None,
        "lower_95ci": finite_float(row.get("lower_95ci", "")),
        "upper_95ci": finite_float(row.get("upper_95ci", "")),
        # Artificial Analysis runs the evaluation itself and says so on every
        # row, so this is not the vendor's own claim about its own model.
        "reported_by": "third_party",
        "measurement_owner": row.get("measurement_owner", "").strip() or None,
        # The source's grouping of its own runs, under its own name. The
        # curated `comparable_group` stays null: see the module docstring.
        "source_comparable_group": row.get("comparable_group", "").strip() or None,
        "comparable_group": None,
        "rank_in_source_response": int(rank) if rank.isdigit() else None,
        "crawled_at": row.get("crawled_at", "").strip() or None,
        # `evaluated_at` is empty on every row, so this dates the model, not
        # the measurement. `date_precision` is what says so.
        "reported_date": row.get("model_release_date", "").strip() or None,
        "date_precision": "model_announcement",
        "methodology_version": row.get("methodology_version", "").strip() or None,
        "source_url": row.get("source_url", "").strip() or None,
    }


def _components(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Each metric component this evaluation published, with its own range.

    Kept inside the series so one series per record key does not mean one
    metric per evaluation. Sorted by name so a rebuild is byte-identical.
    """
    grouped: dict[str, list[dict[str, Any]]] = {}
    for obs in observations:
        grouped.setdefault(obs["metric_component"], []).append(obs)
    components: list[dict[str, Any]] = []
    for name, rows in sorted(grouped.items()):
        values = [row["value"] for row in rows if row["value"] is not None]
        components.append(
            {
                "component": name,
                "unit": rows[0]["unit"],
                "observation_count": len(rows),
                "observed_min": min(values) if values else None,
                "observed_max": max(values) if values else None,
                "normalized_count": sum(
                    1 for row in rows if row["normalized_value_0_100"] is not None
                ),
            }
        )
    return components


def _series(row: dict[str, str], *, key: str, observations: list[dict[str, Any]]) -> dict[str, Any]:
    evaluation_id = row["source_evaluation_id"].strip()
    normalization = row.get("normalization_json", "").strip()
    return {
        "series_id": f"{ARTIFICIAL_ANALYSIS_SOURCE}:{evaluation_id}:default",
        "key": key,
        # Unlike llm-stats, this source names its metric and its direction, so
        # neither is inferred from the rank order.
        "metric": row.get("metric", "").strip() or None,
        "direction": row.get("direction", "").strip() or "higher_is_better",
        "direction_basis": "source_declared",
        "raw_unit": row.get("raw_unit", "").strip() or None,
        "display_unit": row.get("display_unit", "").strip() or None,
        "normalization": json.loads(normalization) if normalization else None,
        "methodology_category": row.get("methodology_category", "").strip() or None,
        "methodology_version": row.get("methodology_version", "").strip() or None,
        "status": row.get("status", "").strip() or None,
        # Components carry the observed ranges. There is no declared ceiling to
        # contradict here: the source publishes units, not a max score.
        "bounds": {"min": None, "max": None, "basis": "source_publishes_no_ceiling"},
        "declared_max": None,
        "observed_max": max(
            (obs["value"] for obs in observations if obs["value"] is not None), default=None
        ),
        "max_score_contradicted": False,
        "display_scale": None,
        "components": _components(observations),
        "observation_count": len(observations),
    }


def _check_manifest(
    manifest: dict[str, Any],
    *,
    evaluations: list[dict[str, str]],
    models: list[dict[str, str]],
    scores: list[dict[str, str]],
    path: Path,
) -> None:
    """Certify the crawl against the counts it shipped with.

    The manifest is the crawler's own statement of what a complete snapshot
    looks like. Checking it here is what makes a truncated file, a partial
    rerun or a silent append fail loudly instead of publishing a snapshot whose
    completeness cannot be stated.
    """
    checks = (
        ("required_evaluation_count", len(evaluations)),
        ("captured_model_count", len(models)),
        ("score_row_count", len(scores)),
    )
    for field, actual in checks:
        declared = manifest.get(field)
        if declared != actual:
            raise ExternalCatalogError(
                f"{path}: manifest declares {field}={declared!r}, snapshot holds {actual}"
            )

    declared_ids = set(manifest.get("required_evaluation_ids") or ())
    actual_ids = {row["source_evaluation_id"].strip() for row in evaluations}
    if declared_ids != actual_ids:
        missing = sorted(declared_ids - actual_ids)
        unexpected = sorted(actual_ids - declared_ids)
        raise ExternalCatalogError(
            f"{path}: evaluation ids do not match the manifest: "
            f"missing {missing}, unexpected {unexpected}"
        )

    declared_per_evaluation = manifest.get("per_evaluation_score_counts") or {}
    actual_per_evaluation: dict[str, int] = {}
    for row in scores:
        evaluation_id = row["source_evaluation_id"].strip()
        actual_per_evaluation[evaluation_id] = actual_per_evaluation.get(evaluation_id, 0) + 1
    if declared_per_evaluation != actual_per_evaluation:
        drifted = sorted(
            evaluation_id
            for evaluation_id in set(declared_per_evaluation) | set(actual_per_evaluation)
            if declared_per_evaluation.get(evaluation_id)
            != actual_per_evaluation.get(evaluation_id)
        )
        raise ExternalCatalogError(f"{path}: per-evaluation score counts drifted: {drifted}")


def _check_identity_candidates(path: Path, evaluation_ids: set[str]) -> dict[str, Any]:
    """Read the source's own review file and refuse any unproven canonical join.

    This file proposes merges; it never performs one. A mapping that names a
    canonical benchmark id on fewer than two independent anchors is rejected
    rather than ignored, so a future hand-edit that reaches too far fails the
    build instead of quietly moving an adoption count.
    """
    if not path.exists():
        raise ExternalCatalogError(f"{path}: Artificial Analysis identity candidates not found")
    document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    mappings = document.get("mappings")
    if not isinstance(mappings, list) or not mappings:
        raise ExternalCatalogError(f"{path}: mappings must be a non-empty array")

    mapped_ids = {str(item.get("source_evaluation_id") or "").strip() for item in mappings}
    if mapped_ids != evaluation_ids:
        raise ExternalCatalogError(
            f"{path}: identity mappings do not cover the evaluations exactly: "
            f"missing {sorted(evaluation_ids - mapped_ids)}, "
            f"unexpected {sorted(mapped_ids - evaluation_ids)}"
        )

    resolved: dict[str, str] = {}
    statuses: dict[str, int] = {}
    for item in mappings:
        status = str(item.get("resolution_status") or "unknown")
        statuses[status] = statuses.get(status, 0) + 1
        canonical = item.get("canonical_benchmark_id")
        if canonical is None:
            continue
        anchors = item.get("evidence") or []
        if len(anchors) < _REQUIRED_IDENTITY_ANCHORS:
            raise ExternalCatalogError(
                f"{path}: {item.get('source_evaluation_id')!r} claims canonical id "
                f"{canonical!r} on {len(anchors)} anchors; "
                f"{_REQUIRED_IDENTITY_ANCHORS} are required"
            )
        resolved[str(item["source_evaluation_id"]).strip()] = str(canonical)

    return {
        "mapping_count": len(mappings),
        "resolution_status_counts": dict(sorted(statuses.items())),
        "resolved_canonical_count": len(resolved),
        "resolved_canonical_ids": dict(sorted(resolved.items())),
    }


def normalize_artificial_analysis(
    snapshot_dir: Path = DEFAULT_SNAPSHOT_DIR,
) -> dict[str, Any]:
    """Turn the committed Artificial Analysis snapshot into catalog records.

    Returns source records, score series and observations in the same shapes
    the llm-stats normalizer emits, plus the validation counts a reviewer needs
    to check the result without rereading three CSVs.
    """
    manifest_path = snapshot_dir / _MANIFEST_FILE
    if not manifest_path.exists():
        raise ExternalCatalogError(f"{manifest_path}: Artificial Analysis manifest not found")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    evaluations_path = snapshot_dir / _EVALUATIONS_FILE
    models_path = snapshot_dir / _MODELS_FILE
    scores_path = snapshot_dir / _SCORES_FILE
    evaluations = _read_csv(evaluations_path)
    models = _read_csv(models_path)
    scores = _read_csv(scores_path)
    _require_columns(
        evaluations,
        ("source_evaluation_id", "name", "metric", "direction", "detail_url", "crawled_at"),
        path=evaluations_path,
    )
    _require_columns(
        models, ("source_model_id", "name", "creator_name", "release_date"), path=models_path
    )
    _require_columns(
        scores,
        ("source_evaluation_id", "source_model_id", "metric_component", "raw_value", "source_rank"),
        path=scores_path,
    )

    _check_manifest(
        manifest,
        evaluations=evaluations,
        models=models,
        scores=scores,
        path=manifest_path,
    )

    models_by_id: dict[str, dict[str, str]] = {}
    for row in models:
        model_id = row["source_model_id"].strip()
        if model_id in models_by_id:
            raise ExternalCatalogError(f"{models_path}: duplicate model id {model_id!r}")
        models_by_id[model_id] = row

    evaluation_ids = {row["source_evaluation_id"].strip() for row in evaluations}
    if len(evaluation_ids) != len(evaluations):
        raise ExternalCatalogError(f"{evaluations_path}: duplicate evaluation ids")
    identity_report = _check_identity_candidates(snapshot_dir / _IDENTITY_FILE, evaluation_ids)

    keys = [f"{ARTIFICIAL_ANALYSIS_KEY_PREFIX}:{item}" for item in sorted(evaluation_ids)]
    slugs = assign_slugs(keys)

    observations_by_evaluation: dict[str, list[dict[str, Any]]] = {}
    seen_obs: set[str] = set()
    for index, row in enumerate(scores):
        evaluation_id = row["source_evaluation_id"].strip()
        model_id = row["source_model_id"].strip()
        if evaluation_id not in evaluation_ids:
            raise ExternalCatalogError(
                f"{scores_path}: row {index} references unknown evaluation {evaluation_id!r}"
            )
        model = models_by_id.get(model_id)
        if model is None:
            raise ExternalCatalogError(
                f"{scores_path}: row {index} references unknown model {model_id!r}"
            )
        key = f"{ARTIFICIAL_ANALYSIS_KEY_PREFIX}:{evaluation_id}"
        observation = _observation(row, model, key=key)
        if observation["obs_id"] in seen_obs:
            raise ExternalCatalogError(
                f"{scores_path}: row {index} repeats observation {observation['obs_id']!r}"
            )
        seen_obs.add(observation["obs_id"])
        observations_by_evaluation.setdefault(evaluation_id, []).append(observation)

    source_records: list[dict[str, Any]] = []
    score_series: list[dict[str, Any]] = []
    score_observations: list[dict[str, Any]] = []
    for row in sorted(evaluations, key=lambda item: item["source_evaluation_id"].strip()):
        evaluation_id = row["source_evaluation_id"].strip()
        key = f"{ARTIFICIAL_ANALYSIS_KEY_PREFIX}:{evaluation_id}"
        observations = observations_by_evaluation.get(evaluation_id, [])
        # Sorted by rank, then component, then model, so a rebuild against
        # unchanged inputs produces byte-identical output.
        observations.sort(
            key=lambda obs: (
                obs["rank_in_source_response"]
                if obs["rank_in_source_response"] is not None
                else 1 << 30,
                obs["metric_component"],
                obs["model_id"],
            )
        )
        source_records.append(_source_record(row, slugs[key]))
        score_series.append(_series(row, key=key, observations=observations))
        score_observations.extend(observations)

    return {
        "source_records": source_records,
        "score_series": score_series,
        "score_observations": score_observations,
        "validation": _validation(
            manifest,
            records=source_records,
            series=score_series,
            observations=score_observations,
            models=models,
            identity=identity_report,
        ),
    }


def write_artificial_analysis_catalog(
    normalized: dict[str, Any],
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Path]:
    """Write the normalized catalog to disk, deterministically.

    Same rule as the llm-stats writer: sorted keys, no build timestamp, so a
    rebuild against unchanged inputs shows an empty diff rather than churn.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "source_records": output_dir / "artificial_analysis_source_records.jsonl",
        "score_series": output_dir / "artificial_analysis_score_series.jsonl",
        "score_observations": output_dir / "artificial_analysis_score_observations.jsonl",
        "validation": output_dir / "artificial_analysis_normalization_validation.json",
    }
    for name in ("source_records", "score_series", "score_observations"):
        paths[name].write_text(
            "".join(
                json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
                for row in normalized[name]
            ),
            encoding="utf-8",
        )
    paths["validation"].write_text(
        json.dumps(normalized["validation"], ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return paths


def _validation(
    manifest: dict[str, Any],
    *,
    records: list[dict[str, Any]],
    series: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    models: list[dict[str, str]],
    identity: dict[str, Any],
) -> dict[str, Any]:
    kinds: dict[str, int] = {}
    components: dict[str, int] = {}
    for obs in observations:
        kinds[obs["value_kind"]] = kinds.get(obs["value_kind"], 0) + 1
        components[obs["metric_component"]] = components.get(obs["metric_component"], 0) + 1

    scored_models = {obs["model_id"] for obs in observations}
    return {
        "schema_version": CATALOG_SCHEMA_VERSION,
        "source": ARTIFICIAL_ANALYSIS_SOURCE,
        "snapshot": manifest.get("snapshot_id"),
        "crawled_at": manifest.get("crawled_at"),
        "methodology_version": manifest.get("methodology_version"),
        "source_record_count": len(records),
        "score_series_count": len(series),
        "score_observation_count": len(observations),
        "obs_id_unique": len({obs["obs_id"] for obs in observations}) == len(observations),
        "model_count": len(models),
        # 618 models were captured, fewer carry a score: a model can be in the
        # source's catalog without appearing on any of the 24 leaderboards.
        "scored_model_count": len(scored_models),
        "models_without_scores": len(models) - len(scored_models),
        "metric_component_distribution": dict(sorted(components.items())),
        "multi_component_evaluations": sorted(
            item["key"] for item in series if len(item["components"]) > 1
        ),
        "value_kind_distribution": dict(sorted(kinds.items())),
        # The source states a group for its own runs on every row, so this
        # fraction is expected to be 0.0. The curated `comparable_group` is
        # null on all 7,050 rows, which is the invariant the registry pins.
        "source_comparable_group_null_fraction": (
            sum(1 for obs in observations if obs["source_comparable_group"] is None)
            / len(observations)
            if observations
            else 1.0
        ),
        "comparable_group_null_fraction": (
            sum(1 for obs in observations if obs["comparable_group"] is None) / len(observations)
            if observations
            else 1.0
        ),
        "normalized_value_null_fraction": (
            sum(1 for obs in observations if obs["normalized_value_0_100"] is None)
            / len(observations)
            if observations
            else 1.0
        ),
        "identity_candidates": identity,
    }
