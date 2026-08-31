"""Reviewed identity enrichment for llm-stats source records.

The llm-stats API does not publish benchmark provenance. Its raw normalized
records therefore remain empty, while this module applies separately reviewed
facts from ``llm_stats_identity_overrides.yml`` before generated source
records, the search index, and detail shards are written.

Repository identity is structural here. A consumer can distinguish a
benchmark's own repository from a shared parent, monorepo subdirectory, or
evaluation harness without parsing prose. Unresolved research is retained too,
but it cannot manufacture an artifact or make ``has_repo`` true.
"""

from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml

from .external_catalog import CATALOG_SCHEMA_VERSION, ExternalCatalogError

DEFAULT_LLM_STATS_IDENTITY_OVERRIDES_PATH = Path("data/external/llm_stats_identity_overrides.yml")

_RESOLUTION_STATUSES = {"resolved", "needs_review", "not_found"}
_RESOLVED_REPO_KINDS = {
    "benchmark_source",
    "shared_parent",
    "monorepo_subdir",
    "harness_only",
}
_REPO_KINDS = _RESOLVED_REPO_KINDS | {"not_found"}
_ANCHOR_TYPES = {"paper", "repo_readme", "dataset_card", "leaderboard", "project_site"}
_OWN_ANCHOR_TYPES = {"paper", "repo_readme", "dataset_card"}
_OPEN_DATA_LICENSES = {
    "MIT",
    "Apache-2.0",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "CC0-1.0",
    "CC-BY-3.0",
    "CC-BY-4.0",
    "CC-BY-SA-4.0",
    "ODC-BY-1.0",
}
_URL_FIELDS = {
    "paper_url": "paper",
    "repo_url": "repo_readme",
    "dataset_url": "dataset_card",
    "site_url": "project_site",
}
_ROW_FIELDS = {
    "resolution_status",
    "repo_kind",
    "repo_url",
    "repo_full_name",
    "repo_subpath",
    "paper_url",
    "dataset_url",
    "site_url",
    "publisher",
    "released",
    "released_basis",
    "code_license",
    "data_license",
    "data_located",
    "sizes",
    "evidence",
    "candidate_matches",
    "note",
}
_FULL_NAME = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_ARXIV_ID = re.compile(r"/(?:abs|pdf|html)/([0-9]{4}\.[0-9]{4,5})(?:v[0-9]+)?(?:\.pdf)?$")


class IdentityOverrideError(ExternalCatalogError):
    """Raised when a reviewed override is malformed or cannot be applied."""


class _UniqueKeyLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate mappings instead of overwriting."""


def _construct_mapping(
    loader: _UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False
) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise IdentityOverrideError(
                f"duplicate YAML key {key!r} at line {key_node.start_mark.line + 1}"
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping,
)


@dataclass(frozen=True)
class LlmStatsIdentityOverrides:
    """Validated override rows plus counts reported by the generator."""

    by_benchmark_id: dict[str, dict[str, Any]]
    validation: dict[str, Any]
    source_path: Path


def _error(path: Path, benchmark_id: str | None, message: str) -> IdentityOverrideError:
    location = str(path)
    if benchmark_id is not None:
        location += f": benchmark {benchmark_id!r}"
    return IdentityOverrideError(f"{location}: {message}")


def _require_url(path: Path, benchmark_id: str, field: str, value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise _error(path, benchmark_id, f"{field} must be a non-empty URL or null")
    text = value.strip()
    parsed = urlsplit(text)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise _error(path, benchmark_id, f"{field} is not an http(s) URL: {text!r}")
    return text


def _normalize_evidence(
    path: Path,
    benchmark_id: str,
    row: dict[str, Any],
) -> list[dict[str, Any]]:
    raw = row.get("evidence")
    evidence: list[dict[str, Any]] = []
    if raw is not None:
        if not isinstance(raw, list):
            raise _error(path, benchmark_id, "evidence must be a list")
        for index, item in enumerate(raw):
            if not isinstance(item, dict):
                raise _error(path, benchmark_id, f"evidence[{index}] must be an object")
            url = _require_url(path, benchmark_id, f"evidence[{index}].url", item.get("url"))
            if url is None:
                raise _error(path, benchmark_id, f"evidence[{index}].url is required")
            anchor_type = item.get("anchor_type")
            claim = item.get("claim")
            if anchor_type not in _ANCHOR_TYPES:
                raise _error(
                    path,
                    benchmark_id,
                    f"evidence[{index}].anchor_type must be one of {sorted(_ANCHOR_TYPES)}",
                )
            if not isinstance(claim, str) or not claim.strip():
                raise _error(path, benchmark_id, f"evidence[{index}].claim is required")
            evidence.append({"url": url, "anchor_type": anchor_type, "claim": claim.strip()})

    # Existing reviewed rows predate the explicit evidence list. Their named
    # artifact URLs still form a mechanical two-URL gate, while the row note
    # records the identity judgement. New research can use the richer list.
    if not evidence:
        note = str(row.get("note") or "").strip()
        for field, anchor_type in _URL_FIELDS.items():
            url = _require_url(path, benchmark_id, field, row.get(field))
            if url:
                evidence.append(
                    {
                        "url": url,
                        "anchor_type": anchor_type,
                        "claim": note,
                    }
                )
    return evidence


def _normalize_candidates(
    path: Path,
    benchmark_id: str,
    raw: Any,
) -> list[dict[str, str]]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise _error(path, benchmark_id, "candidate_matches must be a list")
    candidates: list[dict[str, str]] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise _error(path, benchmark_id, f"candidate_matches[{index}] must be an object")
        url = _require_url(path, benchmark_id, f"candidate_matches[{index}].url", item.get("url"))
        if url is None:
            raise _error(path, benchmark_id, f"candidate_matches[{index}].url is required")
        note = item.get("note")
        if not isinstance(note, str) or not note.strip():
            raise _error(path, benchmark_id, f"candidate_matches[{index}].note is required")
        candidates.append({"url": url, "note": note.strip()})
    return candidates


def _validate_repository(
    path: Path,
    benchmark_id: str,
    row: dict[str, Any],
    status: str,
) -> dict[str, Any]:
    kind = row.get("repo_kind")
    if kind not in _REPO_KINDS:
        raise _error(path, benchmark_id, f"repo_kind must be one of {sorted(_REPO_KINDS)}")

    url = _require_url(path, benchmark_id, "repo_url", row.get("repo_url"))
    full_name = row.get("repo_full_name")
    subpath = row.get("repo_subpath")
    if subpath is not None and (not isinstance(subpath, str) or not subpath.strip()):
        raise _error(path, benchmark_id, "repo_subpath must be a non-empty string or null")
    subpath = subpath.strip().strip("/") if isinstance(subpath, str) else None

    if status == "resolved":
        if kind not in _RESOLVED_REPO_KINDS:
            raise _error(path, benchmark_id, "a resolved row needs a resolved repo_kind")
        if not isinstance(full_name, str) or not _FULL_NAME.fullmatch(full_name):
            raise _error(path, benchmark_id, "repo_full_name must be canonical owner/repo")
        expected_url = f"https://github.com/{full_name}"
        if url is None or url.rstrip("/").lower() != expected_url.lower():
            raise _error(
                path,
                benchmark_id,
                f"repo_url must be the repository root {expected_url!r}; put paths in repo_subpath",
            )
        if kind == "monorepo_subdir" and not subpath:
            raise _error(path, benchmark_id, "monorepo_subdir requires repo_subpath")
    else:
        if kind != "not_found":
            raise _error(path, benchmark_id, f"{status} rows must use repo_kind: not_found")
        if any(value is not None for value in (url, full_name, subpath)):
            raise _error(path, benchmark_id, f"{status} rows cannot publish repository fields")

    return {
        "url": url,
        "full_name": full_name,
        "kind": kind,
        "subpath": subpath,
        "resolution_status": status,
    }


def _validate_row(path: Path, benchmark_id: str, raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise _error(path, benchmark_id, "override must be an object")
    unknown = sorted(set(raw) - _ROW_FIELDS)
    if unknown:
        raise _error(path, benchmark_id, f"unknown fields: {', '.join(unknown)}")

    row = dict(raw)
    status = row.get("resolution_status")
    if status not in _RESOLUTION_STATUSES:
        raise _error(
            path,
            benchmark_id,
            f"resolution_status must be one of {sorted(_RESOLUTION_STATUSES)}",
        )
    note = row.get("note")
    if not isinstance(note, str) or not note.strip():
        raise _error(path, benchmark_id, "note is required")

    for field in _URL_FIELDS:
        row[field] = _require_url(path, benchmark_id, field, row.get(field))
    row["repository"] = _validate_repository(path, benchmark_id, row, status)
    row["evidence"] = _normalize_evidence(path, benchmark_id, row)
    row["candidate_matches"] = _normalize_candidates(
        path, benchmark_id, row.get("candidate_matches")
    )
    row["note"] = note.strip()

    if status == "resolved":
        distinct_urls = {item["url"] for item in row["evidence"]}
        if len(distinct_urls) < 2:
            raise _error(path, benchmark_id, "resolved rows need evidence from two different URLs")
        if not any(item["anchor_type"] in _OWN_ANCHOR_TYPES for item in row["evidence"]):
            raise _error(
                path,
                benchmark_id,
                "resolved rows need a paper, repo_readme, or dataset_card anchor",
            )
    elif not row["candidate_matches"]:
        raise _error(path, benchmark_id, f"{status} rows need at least one candidate_match")

    publisher = row.get("publisher")
    if publisher is not None:
        if not isinstance(publisher, dict) or not str(publisher.get("name") or "").strip():
            raise _error(path, benchmark_id, "publisher needs a name")
        if publisher.get("role") not in {"hub_publisher", "paper_org", "maintainer"}:
            raise _error(path, benchmark_id, "publisher has an unsupported role")

    released = row.get("released")
    if released is not None:
        text = released.isoformat() if isinstance(released, date) else str(released)
        try:
            parsed = date.fromisoformat(text)
        except ValueError as exc:
            raise _error(path, benchmark_id, f"released is not an ISO date: {text!r}") from exc
        if parsed.isoformat() != text:
            raise _error(path, benchmark_id, f"released is not canonical YYYY-MM-DD: {text!r}")
        row["released"] = text
        if not str(row.get("released_basis") or "").strip():
            raise _error(path, benchmark_id, "released needs released_basis")

    sizes = row.get("sizes") or []
    if not isinstance(sizes, list) or any(not isinstance(item, dict) for item in sizes):
        raise _error(path, benchmark_id, "sizes must be a list of objects")
    for index, item in enumerate(sizes):
        missing = [field for field in ("value", "unit", "split", "measures") if field not in item]
        if missing:
            raise _error(path, benchmark_id, f"sizes[{index}] is missing {', '.join(missing)}")

    if row.get("data_located") not in {None, "found", "gated", "not_found"}:
        raise _error(path, benchmark_id, "data_located must be found, gated, not_found, or null")
    return row


def load_llm_stats_identity_overrides(
    records: list[dict[str, Any]],
    path: Path = DEFAULT_LLM_STATS_IDENTITY_OVERRIDES_PATH,
) -> LlmStatsIdentityOverrides:
    """Load and validate every reviewed row against current llm-stats ids."""
    if not path.exists():
        raise IdentityOverrideError(f"{path}: reviewed llm-stats identity overrides not found")
    try:
        data = yaml.load(path.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader) or {}
    except yaml.YAMLError as exc:
        raise IdentityOverrideError(f"{path}: invalid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise IdentityOverrideError(f"{path}: document must be an object")
    if set(data) != {"schema_version", "benchmarks"}:
        raise IdentityOverrideError(
            f"{path}: top-level fields must be schema_version and benchmarks"
        )
    if data.get("schema_version") != CATALOG_SCHEMA_VERSION:
        raise IdentityOverrideError(
            f"{path}: schema_version {data.get('schema_version')!r} != {CATALOG_SCHEMA_VERSION}"
        )
    raw_rows = data.get("benchmarks")
    if not isinstance(raw_rows, dict):
        raise IdentityOverrideError(f"{path}: benchmarks must be an object")

    record_ids = {
        record["source_benchmark_id"] for record in records if record.get("source") == "llm_stats"
    }
    rows: dict[str, dict[str, Any]] = {}
    for benchmark_id, raw in raw_rows.items():
        if not isinstance(benchmark_id, str) or not benchmark_id:
            raise IdentityOverrideError(f"{path}: benchmark ids must be non-empty strings")
        if benchmark_id not in record_ids:
            raise _error(path, benchmark_id, "does not match a current llm-stats source record")
        rows[benchmark_id] = _validate_row(path, benchmark_id, raw)

    status_counts = {
        status: sum(1 for row in rows.values() if row["resolution_status"] == status)
        for status in sorted(_RESOLUTION_STATUSES)
    }
    kind_counts = {
        kind: sum(1 for row in rows.values() if row["repo_kind"] == kind)
        for kind in sorted(_REPO_KINDS)
    }
    return LlmStatsIdentityOverrides(
        by_benchmark_id=rows,
        validation={
            "override_count": len(rows),
            "resolution_status_counts": status_counts,
            "repo_kind_counts": kind_counts,
        },
        source_path=path,
    )


def _artifact_id(kind: str, url: str, repository: dict[str, Any]) -> str:
    if kind == "repo":
        return f"gh:{repository['full_name']}"
    if kind == "paper":
        match = _ARXIV_ID.search(urlsplit(url).path)
        if match:
            return f"arxiv:{match.group(1)}"
    if kind == "dataset":
        parsed = urlsplit(url)
        parts = [part for part in parsed.path.split("/") if part]
        if parsed.netloc.lower() == "huggingface.co" and len(parts) >= 3 and parts[0] == "datasets":
            return f"hf:{parts[1]}/{parts[2]}"
    return f"url:{url}"


def _openness(row: dict[str, Any]) -> dict[str, Any]:
    data_located = row.get("data_located")
    data_license = row.get("data_license")
    if data_located == "gated":
        status, basis = "restricted", "reviewed_data_gated"
    elif data_located == "found" and not data_license:
        status, basis = "restricted", "reviewed_data_found_without_license"
    elif data_located == "found" and data_license not in _OPEN_DATA_LICENSES:
        status, basis = "restricted", "reviewed_data_license_restricts_reuse"
    elif data_located == "found" and data_license:
        status, basis = "open", "reviewed_code_and_licensed_data_public"
    else:
        status, basis = "unknown", "reviewed_data_availability_not_established"
    return {
        "status": status,
        "basis": basis,
        "code_license": row.get("code_license"),
        "code_license_note": None,
        "data_license": data_license,
        "data_license_note": None,
        "data_located": data_located,
        "access_gate": "reviewed_gate" if data_located == "gated" else None,
        "link_status": None,
        "evidence": [
            item["url"]
            for item in row["evidence"]
            if item["anchor_type"] in {"repo_readme", "dataset_card"}
        ],
    }


def _apply_row(record: dict[str, Any], row: dict[str, Any], source_path: Path) -> dict[str, Any]:
    merged = dict(record)
    repository = deepcopy(row["repository"])
    merged["repository"] = repository

    artifacts = list(record.get("artifacts") or [])
    for field, kind in (("paper_url", "paper"), ("repo_url", "repo"), ("dataset_url", "dataset")):
        url = row.get(field)
        if not url:
            continue
        artifact = {
            "kind": kind,
            "id": _artifact_id(kind, url, repository),
            "url": url,
            "locator": f"{source_path}#benchmarks.{record['source_benchmark_id']}.{field}",
        }
        if artifact not in artifacts:
            artifacts.append(artifact)
    merged["artifacts"] = artifacts

    if row.get("publisher"):
        merged["publisher"] = {
            **row["publisher"],
            "locator": f"{source_path}#benchmarks.{record['source_benchmark_id']}.publisher",
        }
    if row.get("released"):
        merged["released"] = row["released"]
        merged["released_basis"] = row.get("released_basis")
    if row.get("sizes"):
        merged["sizes"] = [
            {**item, "origin": "reviewed_llm_stats_identity_override"}
            for item in deepcopy(row["sizes"])
        ]
    merged["openness"] = _openness(row)
    merged["identity_override"] = {
        "source": "reviewed_llm_stats_identity_override",
        "source_path": str(source_path),
        "resolution_status": row["resolution_status"],
        "repository": repository,
        "evidence": deepcopy(row["evidence"]),
        "candidate_matches": deepcopy(row["candidate_matches"]),
        "note": row["note"],
    }
    return merged


def apply_llm_stats_identity_overrides(
    records: list[dict[str, Any]],
    overrides: LlmStatsIdentityOverrides,
) -> list[dict[str, Any]]:
    """Apply reviewed identity without changing keys, scores, or other sources."""
    resolved: list[dict[str, Any]] = []
    seen: set[str] = set()
    for record in records:
        benchmark_id = record.get("source_benchmark_id")
        row = (
            overrides.by_benchmark_id.get(benchmark_id)
            if record.get("source") == "llm_stats"
            else None
        )
        if row is None:
            resolved.append(record)
            continue
        if benchmark_id in seen:
            raise IdentityOverrideError(
                f"duplicate llm-stats source record for benchmark {benchmark_id!r}"
            )
        seen.add(benchmark_id)
        resolved.append(_apply_row(record, row, overrides.source_path))

    missing = sorted(set(overrides.by_benchmark_id) - seen)
    if missing:
        raise IdentityOverrideError(
            "reviewed llm-stats overrides were not applied: " + ", ".join(missing)
        )
    return resolved


def overridden_validation(
    validation: dict[str, Any],
    records: list[dict[str, Any]],
    overrides: LlmStatsIdentityOverrides,
) -> dict[str, Any]:
    """Update the written source-record validation after reviewed enrichment."""
    enriched = dict(validation)
    enriched["identity_overrides"] = overrides.validation
    enriched["empty_provenance_fraction"] = (
        sum(
            1
            for record in records
            if record.get("publisher") is None
            and not record.get("artifacts")
            and not record.get("sizes")
        )
        / len(records)
        if records
        else 1.0
    )
    return enriched
