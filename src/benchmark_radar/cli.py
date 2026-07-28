from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from .pipeline import run_pipeline
from .report import render_markdown
from .snapshots import (
    load_snapshots,
    migrate_snapshot_history,
    rebuild_dashboard,
    write_snapshot,
)


def load_config(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a daily AI benchmark and data radar.")
    parser.add_argument(
        "command",
        nargs="?",
        choices=("run", "rebuild", "backfill", "migrate"),
        default="run",
        help=(
            "Collect a daily run, rebuild/backfill cumulative data from saved snapshots, "
            "or migrate snapshot schemas."
        ),
    )
    parser.add_argument("--config", type=Path, default=Path("config.yml"))
    parser.add_argument("--output", type=Path, default=Path("out/report.md"))
    parser.add_argument("--json-output", type=Path, default=Path("out/items.json"))
    parser.add_argument("--snapshot-dir", type=Path, default=Path("data/snapshots"))
    parser.add_argument("--dashboard-output", type=Path, default=Path("site/data/radar.json"))
    args = parser.parse_args()

    if args.command in {"rebuild", "backfill"}:
        data = rebuild_dashboard(args.snapshot_dir, args.dashboard_output)
        action = "Backfilled" if args.command == "backfill" else "Rebuilt"
        print(f"{action} {args.dashboard_output} from {data['snapshot_count']} daily snapshots")
        return

    config = load_config(args.config)
    if args.command == "migrate":
        snapshots = migrate_snapshot_history(config, args.snapshot_dir)
        dashboard = rebuild_dashboard(args.snapshot_dir, args.dashboard_output)
        print(
            f"Migrated {len(snapshots)} snapshots to schema {dashboard['schema_version']} "
            f"and rebuilt {args.dashboard_output}"
        )
        return

    snapshots = load_snapshots(args.snapshot_dir)
    run = run_pipeline(
        config,
        previous_snapshot=snapshots[-1] if snapshots else None,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    dashboard_url = config.get("publish", {}).get("dashboard_url")
    issue_item_limit = config.get("radar", {}).get("issue_item_limit")
    args.output.write_text(
        render_markdown(
            run,
            dashboard_url=dashboard_url,
            issue_item_limit=int(issue_item_limit) if issue_item_limit else None,
        ),
        encoding="utf-8",
    )
    args.json_output.write_text(
        json.dumps(
            {
                "generated_at": run.generated_at.isoformat(),
                "since": run.since.isoformat(),
                "evidence_items": [item.to_dict() for item in run.items],
                "attention": {
                    "observations": [item.to_dict() for item in run.attention],
                },
                "ingest_health": [
                    health.to_dict() for health in [*run.health, *run.attention_ingest_health]
                ],
                "producer_health": [health.to_dict() for health in run.producer_health],
                "selection": run.selection,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    snapshot_path = write_snapshot(run, args.snapshot_dir)
    dashboard = rebuild_dashboard(args.snapshot_dir, args.dashboard_output)
    print(
        f"Wrote {len(run.items)} items, snapshot {snapshot_path}, and dashboard data "
        f"for {dashboard['snapshot_count']} days"
    )


if __name__ == "__main__":
    main()
