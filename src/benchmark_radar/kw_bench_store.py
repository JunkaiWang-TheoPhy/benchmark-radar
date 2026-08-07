"""Versioned, append-only storage for KW-Bench classifications.

The store is a JSONL file keyed by `(canonical_artifact_id, track_id)`.  JSONL
rather than one JSON document because the backfill writes incrementally and can
be interrupted: a partial JSONL file is a valid prefix of the finished one,
while a partial JSON document is unparseable and loses the whole run.

Two invariants carry the issue's acceptance criteria.

**Idempotence through content hashing.**  A track is re-extracted only when its
metadata fingerprint or the rubric version changes, or when an explicit refresh
cutoff asks for it.  The gate runs *before* extraction, never after: a check
that needs the extracted evidence in hand has already spent the call it was
meant to avoid.  Rerunning a completed backfill therefore performs zero
extraction calls, which is the property that makes a daily run affordable once
the model extractor lands.

**Historical snapshots stay immutable.**  Superseding a record appends a new
row carrying `supersedes_evidence_hash`, rather than editing the old one.  The
earlier row is left exactly as written; `current_records` resolves the live
value by last-row-wins.  A level that changed because the rubric changed must
remain visible as a change, not be silently rewritten into having always been
the new value.

The `superseded` flag that `read_records` honours is reserved for an explicit
retraction (a row withdrawn without a replacement).  Ordinary supersession does
not set it, because the newer row already wins.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Iterator
from datetime import UTC, datetime
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


# Track metadata that is copied into the stored row. A change to any of these
# must invalidate the cache even when the evidence text is byte-identical,
# because the published record would otherwise keep a stale value: an artifact
# promoted from `updated` to `released` that kept its old row would be missing
# from the released-only chart despite having been released.
FINGERPRINTED_TRACK_FIELDS: tuple[str, ...] = (
    "canonical_artifact_id",
    "track_id",
    "track_name",
    "title",
    "url",
    "event_kind",
)


def track_fingerprint(track: dict[str, Any]) -> str:
    """Fingerprint the track metadata that reaches the stored row."""
    payload = {field: str(track.get(field) or "").strip() for field in FINGERPRINTED_TRACK_FIELDS}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()[:16]}"


def _cache_signature(record: dict[str, Any]) -> tuple[str, str, str]:
    """What must match for a stored classification to be reusable.

    The rubric version is part of the signature because a level-boundary change
    invalidates every stored level even when the evidence text is untouched.
    """
    return (
        str(record.get("kw_bench_version") or ""),
        str(record.get("track_fingerprint") or ""),
        str(record.get("extractor") or ""),
    )


def record_changed(previous: dict[str, Any], candidate: dict[str, Any]) -> bool:
    """Whether a freshly classified row differs from the stored one.

    Compared on semantic fields plus cache freshness metadata. Extraction only
    reaches this check for a stale row, so persisting a new extractor identity
    or refresh timestamp prevents the same expensive no-op work on every run.
    """
    fields = (
        "level",
        "level_rationale",
        "evidence_hash",
        "source_hashes",
        "track_fingerprint",
        "review_status",
        "missing_evidence",
        "evidence",
        "tags",
        "kw_bench_version",
        "extractor",
        "classified_at",
    )
    return any(previous.get(field) != candidate.get(field) for field in fields)


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
        lines = handle.readlines()
        for number, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                records.append(json.loads(stripped))
            except json.JSONDecodeError as error:
                # A crash can tear only the row being appended at EOF. Keep
                # the durable prefix resumable, but reject malformed complete
                # lines (and malformed non-final lines) as store corruption.
                if number == len(lines) and not line.endswith("\n"):
                    continue
                raise KwBenchError(f"{path}:{number} is not valid JSON: {error}") from error
    return records


def current_records(path: Path) -> dict[tuple[str, str], dict[str, Any]]:
    """The live classification for each track: the last row wins.

    Later rows supersede earlier ones for the same key, which is what makes an
    append-only file behave as a current-state store without rewriting history.
    """
    live: dict[tuple[str, str], dict[str, Any]] = {}
    for record in read_records(path):
        key = record_key(record)
        if record.get("superseded"):
            live.pop(key, None)
            continue
        live[key] = record
    return live


def needs_classification(
    track: dict[str, Any], cached: dict[str, Any] | None, *, extractor: str
) -> bool:
    """Whether this track must be re-extracted and reclassified.

    Decided from the track and the cached row alone, with no reference to
    freshly extracted evidence, because this gate exists to decide whether to
    *pay for* that extraction.  A check that needs the evidence in hand has
    already spent the call it was meant to avoid.

    Returns False only when a cached row exists whose rubric version, track
    fingerprint, and extractor identity all match. Anything else, including
    an absent cache, a rubric bump, a new extractor, and a track promoted from
    `updated` to `released`, requires work.

    Evidence and source hashes are deliberately not consulted here.  They are
    outputs of extraction, so they cannot gate it; they are compared afterward
    by `record_changed`, which decides whether the result is worth storing.

    A consequence worth stating plainly: an upstream README edit that leaves
    the track metadata untouched does *not* trigger re-extraction on its own,
    because detecting it would require fetching the README, which is the cost
    being avoided.  Refreshing stored evidence against changed upstream text is
    what `--kw-bench-refresh-after` is for.
    """
    if cached is None:
        return True
    return _cache_signature(cached) != (
        KW_BENCH_VERSION,
        track_fingerprint(track),
        extractor,
    )


def is_stale(cached: dict[str, Any] | None, *, refresh_before: str | None) -> bool:
    """Whether a cached row predates the requested refresh cutoff.

    Lets an operator re-extract rows older than a chosen timestamp without
    discarding the whole store, which is the only way to pick up upstream
    source edits that leave a track's metadata unchanged.
    """
    if cached is None or not refresh_before:
        return False

    def timestamp(value: Any, *, field: str) -> datetime:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError as error:
            raise KwBenchError(f"{field} must be an ISO timestamp") from error
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)

    classified_at = cached.get("classified_at")
    if not classified_at:
        return True
    return timestamp(classified_at, field="classified_at") < timestamp(
        refresh_before,
        field="refresh cutoff",
    )


def append_records(path: Path, records: list[dict[str, Any]]) -> int:
    """Append classification rows durably.

    Appends and flushes per batch so an interrupted backfill keeps everything
    written before the interruption.  That is the whole point of the resumable
    contract: progress already paid for is never redone.
    """
    if not records:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size:
        # Recover the append boundary after a torn write. A valid final object
        # merely missing its newline is preserved; an invalid unterminated tail
        # is the interrupted row and is truncated back to the durable prefix.
        with path.open("rb+") as repair:
            contents = repair.read()
            if not contents.endswith(b"\n"):
                boundary = contents.rfind(b"\n") + 1
                tail = contents[boundary:]
                try:
                    json.loads(tail.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    repair.truncate(boundary)
                else:
                    repair.seek(0, os.SEEK_END)
                    repair.write(b"\n")
                repair.flush()
                os.fsync(repair.fileno())
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
