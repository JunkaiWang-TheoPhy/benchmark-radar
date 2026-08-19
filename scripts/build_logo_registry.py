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


def _crawled_organizations() -> set[str]:
    names: set[str] = set()
    for shard in SHARDS.glob("*.json"):
        payloads = json.loads(shard.read_text()).get("scores_by_source") or {}
        for payload in payloads.values():
            for row in payload.get("rows") or []:
                if row.get("organization"):
                    names.add(row["organization"])
    return names


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
    organizations = sorted(curated_orgs | _crawled_organizations())

    # Model families are sampled from curated cards: those carry the real
    # published model names, which is what modelIcon() actually resolves. One
    # entry per (model, organization) pair, sorted for a stable ID.
    models = sorted(
        {(m["model"], m["organization"]) for m in curated_models},
        key=lambda pair: (pair[1], pair[0]),
    )

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
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )
    print(f"organizations: {len(org_ids)}  models: {len(model_ids)} -> {REGISTRY}")


if __name__ == "__main__":
    main()
