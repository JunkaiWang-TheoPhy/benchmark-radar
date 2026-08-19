"""Freeze the organization/model-family IDs the logo audit page cites.

The audit page exists so a wrong brand mark is caught by eye before it ships
(issue #261: Google DeepMind rendered the Google "G", GPT rendered a
hand-drawn rosette, and Meta's path was invented past character 395). Review
feedback has to survive a rebuild, so "O-07" must mean the same organization
next month as it does today. That is what this file freezes: IDs are assigned
once, in sorted order, and an organization that later disappears from the data
keeps its number rather than letting every later card renumber.

Run after `normalize-external` when new organizations appear:

    python scripts/build_logo_registry.py
"""

from __future__ import annotations

import json
from pathlib import Path

REGISTRY = Path("site/data/logo-registry.json")
SHARDS = Path("site/data/benchmarks")
RADAR = Path("site/data/radar.json")


def _crawled() -> tuple[set[str], list[dict[str, str]]]:
    """Organizations and models from the crawled layer.

    A model that draws a point is a model whose mark needs reviewing,
    whichever layer it came from. Reading organizations here while discarding
    the model names in the same loop is what left 75 crawled models with no
    card on the audit page: Gemini had one and MiMo did not, though both draw
    a glyph through the same `modelIcon` call.

    The two layers stay separate in storage -- a curated card is a document
    with a URL and a publication date, a crawled row is an observation with a
    value and no protocol, and forcing them into one record would mean
    inventing the fields the crawled side does not have. They are the same
    only in the way this page cares about: something that resolves to a mark.
    """
    names: set[str] = set()
    models: dict[tuple[str, str], int] = {}
    for shard in SHARDS.glob("*.json"):
        payloads = json.loads(shard.read_text()).get("scores_by_source") or {}
        for payload in payloads.values():
            for row in payload.get("rows") or []:
                organization = row.get("organization")
                if not organization:
                    continue
                names.add(organization)
                model = row.get("model_name")
                if model:
                    models[(model, organization)] = models.get((model, organization), 0) + 1
    return names, [
        {"model": model, "organization": organization}
        for (model, organization) in sorted(models)
    ]


def _curated(radar: dict) -> tuple[set[str], list[dict[str, str]]]:
    board = radar.get("model_card_leaderboard") or {}
    names: set[str] = set()
    models: list[dict[str, str]] = []
    for card in board.get("model_cards") or []:
        organization = card.get("organization")
        if organization:
            names.add(organization)
        if card.get("model") and organization:
            models.append({"model": card["model"], "organization": organization})
    return names, models


def main() -> None:
    radar = json.loads(RADAR.read_text())
    curated_orgs, curated_models = _curated(radar)
    crawled_orgs, crawled_models = _crawled()
    organizations = sorted(curated_orgs | crawled_orgs)

    # Every model that resolves to a mark, from both layers. One entry per
    # (model, organization) pair, sorted for a stable ID. Where a name appears
    # in both layers the curated one wins the label, since it is the record
    # carrying a document behind it.
    layers: dict[tuple[str, str], str] = {}
    for entry in crawled_models:
        layers[(entry["model"], entry["organization"])] = "crawled"
    for entry in curated_models:
        layers[(entry["model"], entry["organization"])] = "curated"
    models = sorted(layers, key=lambda pair: (pair[1], pair[0]))

    previous = json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {}
    org_ids: dict[str, str] = dict(previous.get("organizations") or {})
    model_ids: dict[str, str] = dict(previous.get("models") or {})

    def assign(existing: dict[str, str], keys: list[str], prefix: str) -> None:
        used = {int(v.split("-")[1]) for v in existing.values()} or set()
        nxt = max(used) + 1 if used else 1
        for key in keys:
            if key not in existing:
                existing[key] = f"{prefix}-{nxt:02d}"
                nxt += 1

    assign(org_ids, organizations, "O")
    assign(model_ids, [f"{m}␟{o}" for m, o in models], "M")

    REGISTRY.write_text(
        json.dumps(
            {
                "note": (
                    "Frozen IDs for the logo audit page (site/logos.html). An ID is "
                    "assigned once and never reused, so review feedback citing it "
                    "stays valid across rebuilds."
                ),
                "organizations": dict(sorted(org_ids.items(), key=lambda kv: kv[1])),
                "models": dict(sorted(model_ids.items(), key=lambda kv: kv[1])),
                # Which layer each model came from. The audit page prints it so
                # a crawled row is never read as a curated one: it carries no
                # protocol and no evaluation date, and the two must not look
                # equivalent just because both draw a glyph.
                "model_layers": {
                    f"{model}\u241f{organization}": layer
                    for (model, organization), layer in sorted(
                        layers.items(), key=lambda kv: (kv[0][1], kv[0][0])
                    )
                },
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )
    print(f"organizations: {len(org_ids)}  models: {len(model_ids)} -> {REGISTRY}")


if __name__ == "__main__":
    main()
