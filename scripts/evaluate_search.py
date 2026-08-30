#!/usr/bin/env python3
"""Evaluate local lexical search against sparse, reviewable relevance judgments."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from benchmark_radar.query import QueryPaths, QueryService
from benchmark_radar.search_evaluation import evaluate, load_dataset

DEFAULT_DATASET = Path("tests/fixtures/search_evaluation.yml")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--index", type=Path, default=Path("site/data/benchmark-index.json"))
    parser.add_argument("--shards", type=Path, default=Path("site/data/benchmarks"))
    parser.add_argument("--snapshots", type=Path, default=Path("data/snapshots"))
    return parser


def main() -> int:
    args = _parser().parse_args()
    dataset = load_dataset(args.dataset)
    service = QueryService(
        QueryPaths(index=args.index, shards=args.shards, snapshots=args.snapshots)
    )
    report = evaluate(service, dataset)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
