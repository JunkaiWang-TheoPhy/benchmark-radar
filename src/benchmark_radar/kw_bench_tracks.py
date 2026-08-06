"""Derive canonical benchmark tracks and run the classification backfill.

This is the layer between the corpus and the classifier.  It answers two
questions the classifier deliberately does not: *which* artifacts are scored
benchmark tracks worth classifying, and *where does the evidence come from*.

Track derivation reuses `corpus.artifact_alias_map`, so thousands of daily
observations of the same benchmark collapse to one canonical artifact before
anything expensive happens.  That is step 1 of the issue and it is the reason
the daily run stays cheap: dedup first, then classify, never the reverse.

Evidence extraction is an interface, not an implementation.  The MVP ships a
null extractor that supplies nothing, so every track lands `Unclassified` with
its missing fields recorded.  That is the honest state of a corpus whose
sources publish titles and abstracts rather than verifier documentation.  A
model-backed extractor implements the same `Extractor` protocol and drops in
without touching the decision rules, which stay deterministic either way.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any, Protocol

from . import kw_bench, kw_bench_store
from .corpus import artifact_alias_map, exact_artifact_key

# An artifact enters classification only if it plausibly *introduces a scored
# evaluation track*.  These are the taxonomy categories that make that claim.
# A pure `dataset` record is not a benchmark track: a corpus release with no
# scoring procedure has no capability frontier to locate.
SCORED_TRACK_CATEGORIES = frozenset({"benchmark", "evaluation"})

DEFAULT_BATCH_SIZE = 25


class Extractor(Protocol):
    """Supplies KW-Bench evidence fields for one canonical track.

    Implementations fetch the primary paper, repository README, task
    instructions, and verifier documentation, then return the six evidence
    fields plus the two L5 fields where available.  Returning an empty mapping
    is valid and means "no evidence found", which the classifier renders as
    `Unclassified` rather than a guess.

    `source_hashes` lets the cache detect that a README changed even when the
    extracted evidence text happens to be identical, so a re-extraction is not
    silently skipped after an upstream edit.
    """

    name: str

    def extract(self, track: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
        """Return `(evidence_fields, source_hashes)` for this track."""
        ...


class NullExtractor:
    """The MVP extractor: supplies no evidence.

    Deliberately not a stub that invents plausible fields.  Every track it
    touches becomes `Unclassified` with the full missing-field list, which is
    both the correct rubric outcome and a working end-to-end pipeline that the
    model extractor can be measured against later.
    """

    name = "null"

    def extract(self, track: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
        return {}, []


class MappingExtractor:
    """Serves hand-curated evidence keyed by canonical artifact ID.

    This is how the manually reviewed validation set of issue #153 step 6 is
    supplied, and how L4/L5 records get their evaluator-knowledge claims: a
    human writes the evidence, the deterministic rules assign the level.
    """

    def __init__(self, evidence_by_artifact: dict[str, dict[str, Any]], *, name: str = "curated"):
        self.name = name
        self._evidence = evidence_by_artifact

    def extract(self, track: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
        # Keyed by track ID first so a mixed suite can carry different evidence
        # per track, then by artifact ID for the common single-track case.
        entry = self._evidence.get(str(track.get("track_id"))) or self._evidence.get(
            str(track.get("canonical_artifact_id"))
        )
        if not entry:
            return {}, []
        evidence = dict(entry.get("evidence") or entry)
        sources = [str(value) for value in (entry.get("source_hashes") or [])]
        return evidence, sources


def _is_scored_track(item: dict[str, Any]) -> bool:
    categories = {str(category) for category in (item.get("categories") or [])}
    return bool(categories & SCORED_TRACK_CATEGORIES)


def derive_tracks(
    snapshots: list[dict[str, Any]],
    *,
    track_names: dict[str, list[str]] | None = None,
) -> list[dict[str, Any]]:
    """Collapse snapshot observations into canonical, classifiable tracks.

    One track per canonical artifact by default.  `track_names` splits a known
    mixed suite into several tracks sharing a canonical artifact ID and
    differing by `track_name`, each classified and counted separately, which is
    what the rubric requires of a suite holding both retrieval questions and
    executable tasks.

    The split is supplied, never inferred.  Guessing a suite's task breakdown
    from its title is the keyword inference the rubric forbids, so a suite with
    no declared breakdown stays a single track rather than being invented into
    several.

    The returned rows are deterministic and sorted, so a backfill produces the
    same work list on every machine and every rerun.
    """
    items = [item for snapshot in snapshots for item in snapshot.get("evidence_items", [])]
    aliases = artifact_alias_map(items)
    tracks: dict[str, dict[str, Any]] = {}
    for snapshot in snapshots:
        date = str(snapshot.get("date") or "")
        for item in snapshot.get("evidence_items", []):
            if not _is_scored_track(item):
                continue
            canonical = aliases[exact_artifact_key(item)]
            track = tracks.setdefault(
                canonical,
                {
                    "canonical_artifact_id": canonical,
                    "track_name": "default",
                    "title": str(item.get("title") or ""),
                    "url": str(item.get("url") or ""),
                    "event_kind": "updated",
                    "first_seen_at": date,
                    "last_seen_at": date,
                    "sources": set(),
                    "categories": set(),
                },
            )
            track["first_seen_at"] = min(track["first_seen_at"] or date, date)
            track["last_seen_at"] = max(track["last_seen_at"] or date, date)
            track["sources"].add(str(item.get("source") or ""))
            track["categories"].update(str(value) for value in (item.get("categories") or []))
            # A track counts as released if it was ever seen as a release.  A
            # later "updated" sighting of the same benchmark must not demote it
            # out of the released-only chart, which would make the released
            # count fall as a benchmark gained activity.
            if str(item.get("event_kind")) == "released":
                track["event_kind"] = "released"
                # Prefer the releasing record's own title and URL: an update
                # sighting is often a mirror or a secondary index.
                if str(item.get("title")):
                    track["title"] = str(item["title"])
                if str(item.get("url")):
                    track["url"] = str(item["url"])
    ordered = []
    for canonical in sorted(tracks):
        track = tracks[canonical]
        base = {
            **track,
            "sources": sorted(track["sources"]),
            "categories": sorted(track["categories"]),
        }
        names = (track_names or {}).get(canonical) or [track["track_name"]]
        for name in sorted(dict.fromkeys(str(value) for value in names)):
            ordered.append(
                {
                    **base,
                    "track_name": name,
                    "track_id": kw_bench.track_id(canonical, name),
                }
            )
    return ordered


def classify_tracks(
    tracks: list[dict[str, Any]],
    *,
    store_path: Path,
    classified_at: str,
    extractor: Extractor | None = None,
    batch_size: int = DEFAULT_BATCH_SIZE,
    limit: int | None = None,
    refresh_before: str | None = None,
) -> dict[str, Any]:
    """Classify the tracks that need it and append the results.

    Resumable and idempotent.  A track whose rubric version and metadata
    fingerprint already match a stored row never reaches the extractor, so a
    completed backfill rerun makes zero extraction calls.  Work is committed
    per batch, so an interruption keeps everything already written.

    `refresh_before` re-extracts rows classified before a given timestamp,
    which is how upstream source edits are picked up: they are invisible to the
    fingerprint by construction, since detecting them means fetching the
    source.

    Returns a summary rather than the rows: callers want to know what moved,
    and the store is the record of what exists.
    """
    extractor = extractor or NullExtractor()
    cached = kw_bench_store.current_records(store_path)

    # Decide what is stale *before* extracting anything.  Extraction is the
    # expensive step once a model backs it, so a cache check that runs after it
    # saves nothing: the call has already been paid for.  `track_fingerprint`
    # covers the track metadata that lands in the stored row, so a track whose
    # event_kind flipped to `released` is reclassified even though its evidence
    # text is byte-identical.
    stale = [
        track
        for track in tracks
        if kw_bench_store.needs_classification(
            track,
            cached.get((track["canonical_artifact_id"], track["track_id"])),
        )
        or kw_bench_store.is_stale(
            cached.get((track["canonical_artifact_id"], track["track_id"])),
            refresh_before=refresh_before,
        )
    ]
    reused = len(tracks) - len(stale)
    # `limit` bounds the work, so it must apply to what is left to do rather
    # than to the front of the full list.  Slicing `tracks` made every bounded
    # run re-select the same already-classified prefix, so a corpus larger than
    # the limit could never finish however many times it ran.
    pending = stale[:limit] if limit is not None else stale

    written = 0
    extracted = 0
    superseded = 0
    unchanged = 0
    for batch in kw_bench_store.iter_batches(list(pending), batch_size):
        rows: list[dict[str, Any]] = []
        for track in batch:
            key = (track["canonical_artifact_id"], track["track_id"])
            previous = cached.get(key)
            evidence, source_hashes = extractor.extract(track)
            extracted += 1
            record = kw_bench.classify_track(
                {**track, "evidence": evidence, "source_hashes": source_hashes},
                classified_at=classified_at,
                classified_by=f"kw-bench-deterministic/{extractor.name}",
            )
            record["extractor"] = extractor.name
            record["track_fingerprint"] = kw_bench_store.track_fingerprint(track)
            # Extraction can legitimately return what is already stored: a
            # README edit that did not change the six fields, or a track whose
            # metadata moved without touching its evidence. Appending an
            # identical row would grow the store on every run with no new
            # information, so only a real change is recorded.
            if previous is not None and not kw_bench_store.record_changed(previous, record):
                unchanged += 1
                continue
            # A human-approved level is never silently overwritten by an
            # automated rerun.  Re-approval is a human action, so the new row
            # returns to the review queue and the approval stays visible in
            # history rather than being inherited by different evidence.
            if previous is not None:
                record["supersedes_evidence_hash"] = previous.get("evidence_hash")
                superseded += 1
            rows.append(record)
            cached[key] = record
        written += kw_bench_store.append_records(store_path, rows)

    return {
        "kw_bench_version": kw_bench.KW_BENCH_VERSION,
        "tracks_considered": len(tracks),
        "tracks_pending": len(stale),
        # The honest count of extractor invocations. A cache hit never reaches
        # the extractor, so this is 0 on an unchanged rerun.
        "extraction_calls": extracted,
        "classified": written,
        "reused_from_cache": reused,
        "unchanged_after_extraction": unchanged,
        "superseded": superseded,
        "extractor": extractor.name,
        "store": str(store_path),
    }


def backfill(
    snapshots: list[dict[str, Any]],
    *,
    store_path: Path,
    classified_at: str,
    extractor: Extractor | None = None,
    batch_size: int = DEFAULT_BATCH_SIZE,
    limit: int | None = None,
    refresh_before: str | None = None,
    track_names: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    """Derive tracks from the full snapshot history and classify them."""
    tracks = derive_tracks(snapshots, track_names=track_names)
    summary = classify_tracks(
        tracks,
        store_path=store_path,
        classified_at=classified_at,
        extractor=extractor,
        batch_size=batch_size,
        limit=limit,
        refresh_before=refresh_before,
    )
    return {**summary, "tracks_derived": len(tracks)}


def classification_layer(
    store_path: Path,
    *,
    tracks: Iterable[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build the dashboard payload for the KW-Bench layer.

    Shadow mode: this is published beside the existing taxonomy counts so the
    L0-L5 distribution can be audited against a real corpus before the visible
    chart switches over.  `shadow: True` states that in the payload itself so a
    reader of `radar.json` cannot mistake it for the live chart source.
    """
    records = list(kw_bench_store.current_records(store_path).values())
    return {
        "shadow": True,
        "schema_version": kw_bench.CLASSIFICATION_SCHEMA_VERSION,
        "kw_bench_version": kw_bench.KW_BENCH_VERSION,
        "chart_levels": list(kw_bench.CHART_LEVELS),
        "level_counts": kw_bench.level_counts(records),
        "level_counts_released": kw_bench.level_counts(records, released_only=True),
        "coverage": kw_bench.coverage(records),
        "reference": kw_bench.kw_bench_reference(),
        "track_count": len(list(tracks)) if tracks is not None else len(records),
    }
