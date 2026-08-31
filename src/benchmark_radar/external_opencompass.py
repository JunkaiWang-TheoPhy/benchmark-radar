"""OpenCompass Hub round 2: identity, openness and size, normalized.

llm-stats supplies scores and structurally cannot supply identity: its API
returns eight keys and none is an author, paper, licence or size. OpenCompass
is the other half. Round 1 gave the hub's own card metadata; round 2 resolved
the GitHub and Hugging Face targets those cards point at, and applied the
openness truth table from `docs/external-catalog/STRUCTURE.md`.

WHAT THIS MODULE CLEANS UP

The round 2 export is good but not tidy, and three things are fixed here rather
than sent back for a recrawl:

`NOASSERTION` is GitHub's answer when a LICENSE file exists but its contents
match no known licence. It is the absence of an identification, not a licence,
so it becomes `None` with `license_note: "file_present_unparsed"`. Storing it
verbatim would let a reader see a licence field that is populated and conclude
the licence is known.

Hugging Face `cardData.license` is sometimes a list rather than a string, and a
few values arrived JSON-stringified (`["cc-by-4.0"]`). Those are unwrapped.

Code licences arrive SPDX-cased from the GitHub API (`Apache-2.0`) and data
licences arrive lowercased from Hugging Face (`apache-2.0`). Both are folded to
the SPDX casing so `MIT` and `mit` stop being two licences.

WHAT IS DELIBERATELY NOT CLEANED UP

`openness.status` is copied through exactly as the crawl decided it, along with
the `openness_basis` string naming which truth-table row fired. 272 of 461 are
`unknown`, and 71 of those are unknown only because a linked target timed out.
Re-fetching those is worth doing, but guessing at them here is not: an
`unknown` that a later pass can resolve is honest, and an `open` inferred from
a timeout is not recoverable once published.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .external_catalog import CATALOG_SCHEMA_VERSION, ExternalCatalogError, slugify
from .leaderboard_snapshots import DEFAULT_SNAPSHOTS_PATH, load_snapshots

OPENCOMPASS_SOURCE = "opencompass_hub"
OPENCOMPASS_KEY_PREFIX = "opencompass"
OPENCOMPASS_SNAPSHOT_ID = "opencompass_hub_2026-08-17"
OPENCOMPASS_ROUND2_BUNDLE_ID = "OpenCompassHub_Round2_Public_Evidence_2026-08-18"
DEFAULT_ROUND2_PATH = Path("data/leaderboard_snapshots/opencompass_round2/opencompass_round2.jsonl")

# GitHub's sentinel for "a LICENSE file is present but unidentifiable". Not a
# licence, and it must not be stored as one.
_UNPARSED_LICENSE = "NOASSERTION"

# SPDX casing, so a GitHub `Apache-2.0` and a Hugging Face `apache-2.0` are one
# licence rather than two. Anything unlisted keeps the source's own string.
_SPDX_CASING = {
    "mit": "MIT",
    "apache-2.0": "Apache-2.0",
    "bsd-3-clause": "BSD-3-Clause",
    "bsd-2-clause": "BSD-2-Clause",
    "gpl-2.0": "GPL-2.0",
    "gpl-3.0": "GPL-3.0",
    "agpl-3.0": "AGPL-3.0",
    "lgpl-3.0": "LGPL-3.0",
    "cc0-1.0": "CC0-1.0",
    "cc-by-3.0": "CC-BY-3.0",
    "cc-by-4.0": "CC-BY-4.0",
    "cc-by-sa-4.0": "CC-BY-SA-4.0",
    "cc-by-nc-4.0": "CC-BY-NC-4.0",
    "cc-by-nd-4.0": "CC-BY-ND-4.0",
    "cc-by-nc-sa-4.0": "CC-BY-NC-SA-4.0",
    "cc-by-nc-nd-4.0": "CC-BY-NC-ND-4.0",
    "odc-by": "ODC-By-1.0",
}


def _clean_license(raw: Any) -> tuple[str | None, str | None]:
    """One SPDX id, or None with a note saying why there isn't one."""
    if raw is None:
        return None, None
    value = raw.get("value") if isinstance(raw, dict) else raw
    if isinstance(value, list):
        value = value[0] if value else None
    if not isinstance(value, str):
        return None, None
    text = value.strip()
    # A few arrived JSON-stringified, e.g. '["cc-by-4.0"]'.
    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = json.loads(text)
            text = str(parsed[0]).strip() if isinstance(parsed, list) and parsed else ""
        except json.JSONDecodeError:
            text = text.strip("[]\"' ")
    if not text or text.lower() in {"unknown", "none", "none_found", "other"}:
        return None, None
    if text == _UNPARSED_LICENSE:
        return None, "file_present_unparsed"
    return _SPDX_CASING.get(text.lower(), text), None


def _artifacts(record: dict[str, Any]) -> list[dict[str, Any]]:
    """Paper, repo and dataset links with the locator each was read from."""
    evidence = record.get("identity_evidence") or {}
    artifacts: list[dict[str, Any]] = []
    for kind, field in (("paper", "paper_id"), ("repo", "repo_id"), ("dataset", "dataset_id")):
        for item in evidence.get(field) or []:
            if not isinstance(item, dict):
                continue
            # The export is inconsistent: repo and dataset entries carry the id
            # under `value`, paper entries under `paper_id`. Accept either
            # rather than silently dropping all 408 papers.
            identifier = item.get("value") or item.get(field)
            if not identifier:
                continue
            artifacts.append(
                {
                    "kind": kind,
                    "id": identifier,
                    "url": item.get("evidence_url"),
                    "locator": item.get("locator"),
                }
            )
    return artifacts


def _sizes(record: dict[str, Any]) -> list[dict[str, Any]]:
    """Dataset-viewer counts first, README counts second.

    Viewer counts are exact and per split. README counts are prose and often
    describe training data or a superset, which is why `measures` travels with
    every entry and `unclear` is a common and correct value.
    """
    sizes: list[dict[str, Any]] = []
    for item in (record.get("external_evidence") or {}).get("viewer_sizes") or []:
        sizes.append(
            {
                "value": item.get("value"),
                "unit": item.get("unit"),
                "split": item.get("split"),
                "measures": item.get("measures"),
                "origin": "dataset_viewer",
                "evidence_url": item.get("evidence_url"),
            }
        )
    for item in (record.get("readme_extraction") or {}).get("sizes") or []:
        sizes.append(
            {
                "value": item.get("value"),
                "unit": item.get("unit"),
                "split": item.get("split"),
                "measures": item.get("measures"),
                "origin": "readme",
                "evidence_url": item.get("evidence_url"),
                "evidence_quote": item.get("evidence_quote"),
            }
        )
    return sizes


def _openness(record: dict[str, Any]) -> dict[str, Any]:
    evidence = record.get("external_evidence") or {}
    code_license = None
    code_note = None
    for source in evidence.get("code_sources") or []:
        code_license, code_note = _clean_license(source.get("code_license"))
        if code_license:
            break
    raw_data_license = evidence.get("data_license")
    data_license, data_note = _clean_license(raw_data_license)
    status = (record.get("openness") or {}).get("status") or "unknown"
    if status not in {"open", "restricted", "unknown"}:
        raise ExternalCatalogError(f"unexpected openness status {status!r}")
    return {
        # Copied through, never recomputed. See the module docstring.
        "status": status,
        "basis": (record.get("openness") or {}).get("openness_basis"),
        "code_license": code_license,
        "code_license_note": code_note,
        "data_license": data_license,
        "data_license_note": data_note,
        "data_located": evidence.get("data_located"),
        "access_gate": evidence.get("access_gate"),
        "link_status": evidence.get("link_status"),
        "evidence": [
            item
            for item in (
                evidence.get("data_located_evidence"),
                raw_data_license if isinstance(raw_data_license, dict) else None,
            )
            if item
        ],
    }


def _publisher(record: dict[str, Any]) -> dict[str, Any] | None:
    """The hub's publishing organization, labelled as exactly that.

    `publishOrg` is who published the hub card. That is frequently not the
    benchmark's creator, so the role travels with the name and the site must
    not render it as "made by".
    """
    org = ((record.get("hub_metadata") or {}).get("publish_org") or "").strip()
    if not org:
        return None
    return {"name": org, "role": "hub_publisher", "locator": "detail.basicInfo.publishOrg"}


def _catalog_snapshot(snapshot: dict[str, Any] | None) -> dict[str, Any]:
    """The validated round-1 card snapshot that round 2 enriches.

    Round 2 deliberately contains evidence extracted from GitHub, Hugging Face,
    and card READMEs. It does not repeat the card descriptions, dimensions, and
    tags already retained in the declared round-1 CSV. Both files describe the
    same 461 source ids, so normalization has to join them explicitly rather
    than publish round 2 as if its enrichment fields were the whole record.
    """
    if snapshot is not None:
        if snapshot.get("id") != OPENCOMPASS_SNAPSHOT_ID:
            raise ExternalCatalogError(
                f"expected snapshot {OPENCOMPASS_SNAPSHOT_ID!r}, got {snapshot.get('id')!r}"
            )
        return snapshot
    loaded = load_snapshots(DEFAULT_SNAPSHOTS_PATH)
    matches = [item for item in loaded["snapshots"] if item["id"] == OPENCOMPASS_SNAPSHOT_ID]
    if len(matches) != 1:
        raise ExternalCatalogError(
            f"expected one {OPENCOMPASS_SNAPSHOT_ID!r} snapshot, found {len(matches)}"
        )
    return matches[0]


def _description(row: dict[str, str]) -> dict[str, str]:
    descriptions: dict[str, str] = {}
    for language, fields in (
        ("en", ("detail_description_en", "card_description_en")),
        ("zh", ("detail_description_cn", "card_description_cn")),
    ):
        value = next(
            (row.get(field, "").strip() for field in fields if row.get(field, "").strip()), ""
        )
        if value:
            descriptions[language] = value
    return descriptions


def _provenance(snapshot: dict[str, Any], row: dict[str, Any], round2_path: Path) -> dict[str, Any]:
    """Retain the source lineage for both halves of the joined record."""
    return {
        "source_url": row.get("source_url"),
        "crawled_at": "2026-08-18T00:00:00+00:00",
        "crawl_bundle": OPENCOMPASS_ROUND2_BUNDLE_ID,
        "inputs": {
            "catalog_snapshot": {
                "id": snapshot["id"],
                "source_url": snapshot.get("source_url"),
                "crawled_at": snapshot.get("crawled_at"),
                "file": "data/leaderboard_snapshots/opencompass_hub_catalog_2026-08-17.csv",
            },
            "round2_evidence": {
                "id": OPENCOMPASS_ROUND2_BUNDLE_ID,
                "file": str(round2_path),
                "crawled_at": "2026-08-18T00:00:00+00:00",
            },
        },
    }


def _categories(row: dict[str, str]) -> list[str]:
    """Source-authored tags and dimensions, deduplicated but not inferred."""
    categories: list[str] = []
    seen: set[str] = set()
    for field in ("dimensions", "basic_tags", "topic_tags", "card_tags"):
        for raw in row.get(field, "").split("|"):
            value = raw.strip()
            folded = value.casefold()
            if value and folded not in seen:
                seen.add(folded)
                categories.append(value)
    return categories


def _modality(row: dict[str, str]) -> str | None:
    """Normalize only explicit English values from the Hub's dimensions."""
    dimensions = {
        value.strip().casefold() for value in row.get("dimensions", "").split("|") if value.strip()
    }
    if "multimodal" in dimensions:
        return "multimodal"
    if "video-understanding" in dimensions:
        return "video"
    if dimensions & {"visual-qa", "visual-localization", "spatial-understanding"}:
        return "image"
    return None


def normalize_opencompass(
    path: Path = DEFAULT_ROUND2_PATH,
    *,
    catalog_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Join the card snapshot and round-2 evidence into shared catalog records."""
    if not path.exists():
        raise ExternalCatalogError(f"{path}: OpenCompass round 2 export not found")
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]

    snapshot = _catalog_snapshot(catalog_snapshot)
    catalog_rows: dict[str, dict[str, str]] = {}
    for row in snapshot["benchmark_rows"]:
        source_id = str(row.get("benchmark_id") or "").strip()
        if not source_id:
            raise ExternalCatalogError("OpenCompass card snapshot contains an empty benchmark_id")
        if source_id in catalog_rows:
            raise ExternalCatalogError(
                f"OpenCompass card snapshot repeats benchmark_id {source_id!r}"
            )
        catalog_rows[source_id] = row

    round2_id_values = [str(row.get("benchmark_id") or "").strip() for row in rows]
    if not all(round2_id_values):
        raise ExternalCatalogError("OpenCompass round-2 export contains an empty benchmark_id")
    if len(round2_id_values) != len(set(round2_id_values)):
        raise ExternalCatalogError("OpenCompass round-2 export repeats a benchmark_id")
    round2_ids = set(round2_id_values)
    catalog_ids = set(catalog_rows)
    if round2_ids != catalog_ids:
        missing_round2 = sorted(catalog_ids - round2_ids)
        missing_catalog = sorted(round2_ids - catalog_ids)
        raise ExternalCatalogError(
            "OpenCompass card and round-2 benchmark ids differ: "
            f"missing_round2={missing_round2[:5]}, missing_catalog={missing_catalog[:5]}"
        )

    records: list[dict[str, Any]] = []
    used: dict[str, int] = {}
    for row in sorted(rows, key=lambda item: str(item["benchmark_id"])):
        source_id = str(row["benchmark_id"])
        key = f"{OPENCOMPASS_KEY_PREFIX}:{source_id}"
        base = slugify(f"{key}-{row.get('name') or ''}")
        count = used.get(base, 0) + 1
        used[base] = count
        readme = row.get("readme_extraction") or {}
        identity = row.get("identity_evidence") or {}
        card = catalog_rows[source_id]
        records.append(
            {
                "key": key,
                "slug": base if count == 1 else f"{base}-{count}",
                "schema_version": CATALOG_SCHEMA_VERSION,
                "source": OPENCOMPASS_SOURCE,
                "source_benchmark_id": source_id,
                "name": (row.get("name") or source_id).strip(),
                "description": _description(card),
                "publisher": _publisher(row),
                "artifacts": _artifacts(row),
                "openness": _openness(row),
                "sizes": _sizes(row),
                "released": ((row.get("hub_metadata") or {}).get("release_date") or None),
                "modality": _modality(card),
                "categories": _categories(card),
                "languages": [item.get("value") for item in readme.get("languages") or []],
                "version_reported": (
                    identity.get("version_reported") or readme.get("version_reported")
                ),
                "possible_variant": bool(identity.get("possible_variant")),
                "provenance": _provenance(snapshot, row, path),
            }
        )

    return {"source_records": records, "validation": _validation(records)}


def _validation(records: list[dict[str, Any]]) -> dict[str, Any]:
    def count(predicate: Any) -> int:
        return sum(1 for item in records if predicate(item))

    status: dict[str, int] = {}
    for item in records:
        key = item["openness"]["status"]
        status[key] = status.get(key, 0) + 1
    return {
        "schema_version": CATALOG_SCHEMA_VERSION,
        "source": OPENCOMPASS_SOURCE,
        "source_record_count": len(records),
        "openness_status_counts": dict(sorted(status.items())),
        "with_publisher": count(lambda item: item["publisher"] is not None),
        "with_description": count(lambda item: bool(item["description"])),
        "with_categories": count(lambda item: bool(item["categories"])),
        "with_modality": count(lambda item: bool(item["modality"])),
        "with_paper": count(lambda i: any(a["kind"] == "paper" for a in i["artifacts"])),
        "with_repo": count(lambda i: any(a["kind"] == "repo" for a in i["artifacts"])),
        "with_dataset": count(lambda i: any(a["kind"] == "dataset" for a in i["artifacts"])),
        "with_sizes": count(lambda item: bool(item["sizes"])),
        "with_code_license": count(lambda item: item["openness"]["code_license"]),
        "with_data_license": count(lambda item: item["openness"]["data_license"]),
        "license_file_present_unparsed": count(
            lambda item: item["openness"]["code_license_note"] == "file_present_unparsed"
        ),
        "with_released": count(lambda item: item["released"]),
    }
