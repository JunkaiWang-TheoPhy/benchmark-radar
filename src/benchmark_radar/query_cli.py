"""CLI commands for local Benchmark Radar discovery."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .data_store import DEFAULT_MANIFEST_URL, DataStore
from .query import (
    SEARCH_SCOPES,
    QueryError,
    QueryPaths,
    QueryService,
    error_payload,
)
from .query_http import serve_query_api

QUERY_COMMANDS = frozenset({"init", "sync", "search", "show", "recent", "status", "serve"})


def _data_parent() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--data-dir", type=Path, default=None)
    parser.add_argument("--index", type=Path, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--shards", type=Path, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--snapshots", type=Path, default=None, help=argparse.SUPPRESS)
    return parser


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="benchmark-radar",
        description="Search the local Benchmark Radar catalog and daily Radar history.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    data_parent = _data_parent()

    init = subparsers.add_parser("init", help="Download and verify the current dataset.")
    init.add_argument("--data-dir", type=Path, default=None)
    init.add_argument("--manifest-url", default=DEFAULT_MANIFEST_URL)
    init.add_argument("--json", action="store_true")

    sync = subparsers.add_parser("sync", help="Update an initialized local dataset.")
    sync.add_argument("--data-dir", type=Path, default=None)
    sync.add_argument("--json", action="store_true")

    search = subparsers.add_parser(
        "search", parents=[data_parent], help="Search benchmark catalog and Radar records."
    )
    search.add_argument("query")
    search.add_argument("--scope", choices=SEARCH_SCOPES, default="catalog")
    search.add_argument("--limit", type=int, default=20)
    search.add_argument("--has-paper", action=argparse.BooleanOptionalAction, default=None)
    search.add_argument("--has-repo", action=argparse.BooleanOptionalAction, default=None)
    search.add_argument("--has-dataset", action=argparse.BooleanOptionalAction, default=None)
    search.add_argument("--openness")
    search.add_argument("--modality")
    search.add_argument("--source")
    search.add_argument("--json", action="store_true")

    show = subparsers.add_parser(
        "show", parents=[data_parent], help="Show one catalog record by key or slug."
    )
    show.add_argument("identifier")
    show.add_argument("--json", action="store_true")

    recent = subparsers.add_parser(
        "recent", parents=[data_parent], help="List evidence from the latest Radar snapshot."
    )
    recent.add_argument("--limit", type=int, default=20)
    recent.add_argument("--category")
    recent.add_argument("--source")
    recent.add_argument("--recommended", action="store_true")
    recent.add_argument("--json", action="store_true")

    status = subparsers.add_parser(
        "status", parents=[data_parent], help="Inspect local catalog and snapshot health."
    )
    status.add_argument("--json", action="store_true")

    serve = subparsers.add_parser(
        "serve", parents=[data_parent], help="Serve the same query contract over local HTTP."
    )
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    return parser


def _service(args: argparse.Namespace) -> QueryService:
    explicit = (args.index, args.shards, args.snapshots)
    if any(value is not None for value in explicit):
        if not all(value is not None for value in explicit):
            raise QueryError(
                "--index, --shards, and --snapshots must be passed together",
                code="invalid_paths",
                status=400,
            )
        return QueryService(
            QueryPaths(index=args.index, shards=args.shards, snapshots=args.snapshots)
        )
    return QueryService(DataStore(root=args.data_dir).query_paths())


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def _print_search(payload: dict[str, Any]) -> None:
    if payload["search_status"] == "no_lexical_candidates":
        print(f"No lexical candidates found (scope={payload['scope']}).")
        return
    print(
        f"{payload['count']} of {payload['total_matches']} lexical candidates "
        f"({payload['retrieval_mode']}, scope={payload['scope']})"
    )
    for item in payload["results"]:
        locator = item.get("slug") or item["key"]
        print(f"{item['rank']:>3}. {item['name']}  [{item['kind']}]  {locator}")
        print(f"     {item['match']['reason']}; fields={','.join(item['match']['matched_fields'])}")


def _print_recent(payload: dict[str, Any]) -> None:
    print(f"{payload['count']} Radar items from {payload['date']}")
    for index, item in enumerate(payload["results"], start=1):
        print(f"{index:>3}. {item['title']}  [{item['source']}]  {item['source_id']}")


def _print_show(payload: dict[str, Any]) -> None:
    record = payload["benchmark"]["record"]
    print(f"{record['name']}\nkey: {record['key']}\nslug: {record['slug']}")
    print(f"source: {record['source']}\nopenness: {(record.get('openness') or {}).get('status')}")
    artifacts = record.get("artifacts") or []
    if artifacts:
        print("artifacts:")
        for artifact in artifacts:
            print(f"  {artifact.get('kind')}: {artifact.get('url')}")


def _print_status(payload: dict[str, Any]) -> None:
    print(f"status: {payload['status']}")
    print(f"catalog: {payload['catalog']['count']} records at {payload['catalog']['path']}")
    print(
        f"radar: {payload['radar']['snapshot_count']} snapshots; "
        f"latest={payload['radar']['latest_date']}"
    )
    gaps = payload["radar"]["required_coverage_gaps"]
    print(f"required source gaps: {', '.join(gaps) if gaps else 'none'}")


def _print_sync(payload: dict[str, Any]) -> None:
    print(f"data: {payload['status']} ({payload['data_version']})")
    print(f"location: {payload['data_home']}")
    if payload.get("cleanup_pending"):
        print("cleanup: pending; the next sync will retry obsolete data removal")


def run_query_cli(argv: Sequence[str] | None = None) -> int:
    """Run one query command and return a process-style exit code."""

    args = _parser().parse_args(argv)
    try:
        if args.command == "init":
            payload = DataStore(root=args.data_dir, manifest_url=args.manifest_url).initialize()
            _print_json(payload) if args.json else _print_sync(payload)
            return 0
        if args.command == "sync":
            payload = DataStore(root=args.data_dir).sync()
            _print_json(payload) if args.json else _print_sync(payload)
            return 0

        service = _service(args)
        if args.command == "search":
            payload = service.search(
                args.query,
                scope=args.scope,
                limit=args.limit,
                has_paper=args.has_paper,
                has_repo=args.has_repo,
                has_dataset=args.has_dataset,
                openness=args.openness,
                modality=args.modality,
                source=args.source,
            )
            _print_json(payload) if args.json else _print_search(payload)
            return 0
        if args.command == "show":
            payload = service.show(args.identifier)
            _print_json(payload) if args.json else _print_show(payload)
            return 0
        if args.command == "recent":
            payload = service.recent(
                limit=args.limit,
                category=args.category,
                source=args.source,
                recommended=args.recommended,
            )
            _print_json(payload) if args.json else _print_recent(payload)
            return 0
        if args.command == "status":
            payload = service.status()
            _print_json(payload) if args.json else _print_status(payload)
            return 0
        if args.command == "serve":
            logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
            status = service.status()
            if not status["catalog"]["complete"]:
                raise QueryError(
                    "catalog detail shards are incomplete; run `benchmark-radar sync`",
                    code="data_unavailable",
                    status=503,
                )
            print(f"Serving Benchmark Radar at http://{args.host}:{args.port}", file=sys.stderr)
            serve_query_api(service, host=args.host, port=args.port)
            return 0
    except QueryError as error:
        print(json.dumps(error_payload(error), ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 2 if 400 <= error.status < 500 else 1
    raise AssertionError(f"unhandled query command: {args.command}")
