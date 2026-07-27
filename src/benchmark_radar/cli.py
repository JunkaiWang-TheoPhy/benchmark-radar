from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from .pipeline import run_pipeline
from .report import render_markdown


def load_config(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a daily AI benchmark and data radar.")
    parser.add_argument("--config", type=Path, default=Path("config.yml"))
    parser.add_argument("--output", type=Path, default=Path("out/report.md"))
    parser.add_argument("--json-output", type=Path, default=Path("out/items.json"))
    args = parser.parse_args()

    config = load_config(args.config)
    run = run_pipeline(config)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_markdown(run), encoding="utf-8")
    args.json_output.write_text(
        json.dumps(
            {
                "generated_at": run.generated_at.isoformat(),
                "since": run.since.isoformat(),
                "items": [item.to_dict() for item in run.items],
                "health": [
                    {
                        "source": health.source,
                        "ok": health.ok,
                        "item_count": health.item_count,
                        "error": health.error,
                    }
                    for health in run.health
                ],
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(run.items)} items to {args.output} and {args.json_output}")


if __name__ == "__main__":
    main()

