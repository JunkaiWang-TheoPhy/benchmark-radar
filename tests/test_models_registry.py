"""One structure for models, whichever layer reported them.

A curated model card and a crawled score row shared exactly one field name --
`organization` -- because the project modelled the two things that *mention* a
model and never the model itself. Asking "which models do we know about?" meant
walking two structures, and any consumer that forgot the second silently
dropped 321 models: Gemini had a record and MiMo did not.
"""

from __future__ import annotations

import json
from pathlib import Path

from benchmark_radar.models_registry import (
    CRAWLED,
    CURATED,
    build_registry,
    model_key,
    summarize,
)


def _registry():
    radar = json.loads(Path("site/data/radar.json").read_text(encoding="utf-8"))
    return build_registry(radar, Path("site/data/benchmarks"))


def test_a_model_is_one_record_no_matter_which_layer_reported_it():
    registry = _registry()

    gemini = [r for r in registry.values() if "Gemini" in r.model]
    mimo = [r for r in registry.values() if "MiMo" in r.model]
    assert gemini, "no Gemini record"
    assert mimo, "no MiMo record -- the gap this structure exists to close"

    # Same shape, same fields, same treatment. Neither is a special case.
    for record in gemini + mimo:
        assert record.key and record.model and record.organization
        assert record.sources
        assert set(record.layers) <= {CURATED, CRAWLED}


def test_a_model_both_layers_reported_is_one_record_carrying_both():
    """The join the old two-list shape could not express at all.

    Claude Opus 5 and DeepSeek-V3 exist as a curated card AND as crawled rows.
    Stored as two lists they were two unrelated entries; here they are one
    record whose `layers` names both.
    """
    registry = _registry()
    both = [r for r in registry.values() if len(r.layers) > 1]

    assert len(both) >= 10, "expected models present in both layers"
    for record in both:
        assert record.layers == [CURATED, CRAWLED]
        assert {s.layer for s in record.sources} == {CURATED, CRAWLED}


def test_evidence_stays_labelled_rather_than_flattened():
    """Unified record, per-source evidence.

    A curated card establishes a document; a crawled row establishes an
    observation with no protocol and no evaluation date. Flattening them would
    let a crawled row inherit a document it does not have, which is the
    confident wrong attribution this codebase refuses to make.
    """
    registry = _registry()

    for record in registry.values():
        for entry in record.sources:
            assert entry.layer in (CURATED, CRAWLED)
            if entry.layer == CRAWLED:
                # Never promoted onto the record itself.
                assert entry.payload.get("comparable_group") is None
                assert "url" not in entry.payload or entry.payload.get("source_url")

    # And the record carries no field that only one layer could support.
    sample = next(iter(registry.values()))
    assert set(sample.to_dict()) == {"key", "model", "organization", "layers", "sources"}


def test_the_key_is_stable_and_safe():
    assert model_key("MiMo-V2.5-Pro", "Xiaomi") == "xiaomi-mimo-v2-5-pro"
    assert model_key("Gemini 3.1 Pro", "Google") == "google-gemini-3-1-pro"
    # Same name from two organizations is two models, not one.
    assert model_key("Nova", "Amazon") != model_key("Nova", "Meta")


def test_the_published_registry_matches_what_the_builder_produces():
    published = json.loads(Path("site/data/models.json").read_text(encoding="utf-8"))
    report = summarize(_registry())

    for field in ("model_count", "curated_only", "crawled_only", "both_layers"):
        assert published[field] == report[field], field
    assert len(published["models"]) == published["model_count"]
    # The published form is an index: identity and layer, not embedded payloads.
    assert set(published["models"][0]) == {
        "key",
        "model",
        "organization",
        "layers",
        "source_counts",
    }
