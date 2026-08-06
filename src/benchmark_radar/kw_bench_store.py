"""Versioned, append-only storage for KW-Bench classifications.

The store is a JSONL file keyed by `(canonical_artifact_id, track_id)`.  JSONL
rather than one JSON document because the backfill writes incrementally and can
be interrupted: a partial JSONL file is a valid prefix of the finished one,
while a partial JSON document is unparseable and loses the whole run.

Two invariants carry the issue's acceptance criteria.

**Idempotence through content hashing.**  A track is reclassified only when its
evidence hash, its source hashes, or the rubric version changes.  Rerunning a
completed backfill therefore performs zero extraction calls, which is the
property that makes a daily run affordable once the model extractor lands.

**Historical snapshots stay immutable.**  Superseding a record appends the new
row and marks the old one, rather than editing in place.  A level that changed
because the rubric changed must remain visible as a change, not be silently
rewritten into having always been the new value.
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from .kw_bench import KW_BENCH_VERSION, KwBenchError

STORE_FILENAME = "kw_bench_classifications.jsonl"


def record_key(record: dict[str, Any]) -> tuple[str, str]:
    """The identity of a classification row."""
    return (
        str(record.get("canonical_artifact_id") or ""),
        str(record.get("track_id") or ""),
    )


def _cache_signature(record: dict[str, Any]) -> tuple[str, tuple[str, ...], str]:
    """What must match for a stored classification to be reusable.

    The rubric version is part of the signature because a level-boundary change
    invalidates every stored level even when the evidence text is untouched.
    """
    return (
        str(record.get("evidence_hash") or ""),
        tuple(str(value) for value in (record.get("source_hashes") or [])),
        str(record.get("kw_bench_version") or ""),
    )


def read_records(path: Path) -> list[dict[str, Any]]:
    """Load every row, including superseded ones.

    A blank line is skipped rather than treated as an error: an interrupted
    write can leave one, and refusing to load the file would turn a recoverable
    partial run into a lost one.
    """
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                records.append(json.loads(stripped))
            except json.JSONDecodeError as error:
                raise KwBenchError(f"{path}:{number} is not valid JSON: {error}") from error
    return records


def current_records(path: Path) -> dict[tuple[str, str], dict[str, Any]]:
    """The live classification for each track: the last row wins.

    Later rows supersede earlier ones for the same key, which is what makes an
    append-only file behave as a current-state store without rewriting history.
    """
    live: dict[tuple[str, str], dict[str, Any]] = {}
    for record in read_records(path):
        if record.get("superseded"):
            continue
        live[record_key(record)] = record
    return live


def needs_classification(
    track: dict[str, Any],
    cached: dict[str, Any] | None,
    *,
    evidence_hash: str,
    source_hashes: Iterable[str] = (),
) -> bool:
    """Whether this track must be reclassified.

    Returns False only when a cached row exists whose evidence, sources, and
    rubric version all match.  Anything else, including an absent cache and a
    rubric bump, requires work.
    """
    if cached is None:
        return True
    signature = (
        str(evidence_hash),
        tuple(sorted(str(value) for value in source_hashes)),
        KW_BENCH_VERSION,
    )
    return _cache_signature(cached) != signature


def append_records(path: Path, records: list[dict[str, Any]]) -> int:
    """Append classification rows durably.

    Appends and flushes per batch so an interrupted backfill keeps everything
    written before the interruption.  That is the whole point of the resumable
    contract: progress already paid for is never redone.
    """
    if not records:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return len(records)


def rewrite_records(path: Path, records: list[dict[str, Any]]) -> int:
    """Replace the store atomically.

    Used by compaction only.  Writes to a temporary file in the same directory
    and renames, so a crash mid-write leaves the previous store intact rather
    than a truncated one.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    )
    temporary = Path(handle.name)
    try:
        with handle:
            for record in records:
                handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return len(records)


def iter_batches(items: list[Any], size: int) -> Iterator[list[Any]]:
    """Split work into bounded batches.

    The backfill processes batches rather than the whole corpus so a rate limit
    or a crash costs one batch of progress instead of the entire run.
    """
    if size <= 0:
        raise KwBenchError("batch size must be positive")
    for start in range(0, len(items), size):
        yield items[start : start + size]
