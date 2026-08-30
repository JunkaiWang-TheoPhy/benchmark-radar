#!/usr/bin/env python3
"""Build the public contributor-point ledger from canonical GitHub metadata."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

POINTS_RE = re.compile(r"^\[([1-9][0-9]*) points?\](?:\s|$)", re.IGNORECASE)
POLICY_START = datetime(2026, 8, 30, tzinfo=UTC)
CLAIM_WINDOW = timedelta(days=7)
COLLABORATOR_THRESHOLD = 6
OWNER = "ktwu01"


def parse_points(title: str) -> int | None:
    """Return a positive title-prefix score, with no artificial upper bound."""
    match = POINTS_RE.match(title)
    return int(match.group(1)) if match else None


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def is_automation(login: str) -> bool:
    lowered = login.lower()
    return lowered.startswith("app/") or lowered.endswith("[bot]")


def latest_assignment(events: list[dict[str, Any]], login: str) -> datetime | None:
    matching = [
        parse_time(event.get("created_at"))
        for event in events
        if event.get("event") == "assigned" and (event.get("assignee") or {}).get("login") == login
    ]
    return max((time for time in matching if time is not None), default=None)


def evaluate_issue(
    issue: dict[str, Any],
    pull_requests: dict[int, dict[str, Any]],
    events: list[dict[str, Any]],
    *,
    policy_start: datetime = POLICY_START,
    now: datetime | None = None,
) -> dict[str, Any] | None:
    """Evaluate one post-policy issue claim."""
    points = parse_points(issue.get("title", ""))
    if points is None:
        return None

    assignees = [item["login"] for item in issue.get("assignees", [])]
    record: dict[str, Any] = {
        "kind": "issue",
        "number": issue["number"],
        "url": issue.get("url"),
        "title": issue.get("title"),
        "points": points,
        "earned_points": 0,
        "assignees": assignees,
    }
    if not assignees:
        record["status"] = "ready" if issue.get("state") == "OPEN" else "invalid"
        record["reason"] = "no assignee"
        return record
    if len(assignees) != 1:
        record["status"] = "invalid"
        record["reason"] = "a scored issue must have exactly one assignee"
        return record

    login = assignees[0]
    assigned_at = latest_assignment(events, login)
    if assigned_at is None or assigned_at < policy_start:
        record["status"] = "invalid"
        record["reason"] = "no post-policy assignment event for the current assignee"
        return record

    deadline = assigned_at + CLAIM_WINDOW
    record.update(
        {
            "contributor": login,
            "assigned_at": assigned_at.isoformat(),
            "deadline": deadline.isoformat(),
        }
    )
    now = now or datetime.now(UTC)
    if issue.get("state") == "OPEN":
        record["status"] = "active" if now <= deadline else "expired"
        return record

    closed_at = parse_time(issue.get("closedAt"))
    if issue.get("stateReason") != "COMPLETED":
        record["status"] = "invalid"
        record["reason"] = "issue was not closed as completed"
        return record
    if closed_at is None or closed_at > deadline:
        record["status"] = "expired"
        record["reason"] = "issue was not completed inside 168 hours"
        return record

    closing_numbers = [item["number"] for item in issue.get("closedByPullRequestsReferences", [])]
    qualifying_prs = []
    for number in closing_numbers:
        pull_request = pull_requests.get(number)
        if not pull_request:
            continue
        author = (pull_request.get("author") or {}).get("login")
        merged_at = parse_time(pull_request.get("mergedAt"))
        if author == login and merged_at and assigned_at <= merged_at <= deadline:
            qualifying_prs.append(number)
    if not qualifying_prs:
        record["status"] = "invalid"
        record["reason"] = "no timely merged closing pull request by the assignee"
        return record

    record.update(
        {
            "status": "earned",
            "earned_points": points,
            "completed_at": closed_at.isoformat(),
            "pull_requests": qualifying_prs,
            "automation": is_automation(login),
        }
    )
    return record


def evaluate_historical_pr(
    pull_request: dict[str, Any],
    *,
    policy_start: datetime = POLICY_START,
    owner: str = OWNER,
) -> dict[str, Any] | None:
    """Credit one prefixed, pre-policy PR by someone other than the owner."""
    points = parse_points(pull_request.get("title", ""))
    author = (pull_request.get("author") or {}).get("login", "")
    merged_at = parse_time(pull_request.get("mergedAt"))
    if (
        points is None
        or not author
        or author == owner
        or merged_at is None
        or merged_at >= policy_start
    ):
        return None
    return {
        "kind": "historical_pr",
        "number": pull_request["number"],
        "url": pull_request.get("url"),
        "title": pull_request.get("title"),
        "contributor": author,
        "points": points,
        "earned_points": points,
        "status": "earned",
        "completed_at": merged_at.isoformat(),
        "automation": is_automation(author),
    }


def build_ledger(
    issues: list[dict[str, Any]],
    pull_requests: list[dict[str, Any]],
    events_by_issue: dict[int, list[dict[str, Any]]],
    *,
    policy_start: datetime = POLICY_START,
    now: datetime | None = None,
) -> dict[str, Any]:
    pr_by_number = {item["number"]: item for item in pull_requests}
    contributions = [
        record
        for issue in issues
        if (
            record := evaluate_issue(
                issue,
                pr_by_number,
                events_by_issue.get(issue["number"], []),
                policy_start=policy_start,
                now=now,
            )
        )
    ]
    contributions.extend(
        record
        for pull_request in pull_requests
        if (record := evaluate_historical_pr(pull_request, policy_start=policy_start))
    )

    totals: dict[str, int] = defaultdict(int)
    automation: set[str] = set()
    for record in contributions:
        contributor = record.get("contributor")
        if contributor and record["earned_points"]:
            totals[contributor] += record["earned_points"]
            if record.get("automation"):
                automation.add(contributor)
    people = [
        {
            "contributor": contributor,
            "points": points,
            "eligible_for_collaborator_seat": contributor not in automation
            and points >= COLLABORATOR_THRESHOLD,
        }
        for contributor, points in sorted(
            totals.items(), key=lambda item: (-item[1], item[0].lower())
        )
    ]
    return {
        "generated_at": (now or datetime.now(UTC)).isoformat(),
        "policy_start": policy_start.isoformat(),
        "claim_window_hours": int(CLAIM_WINDOW.total_seconds() / 3600),
        "collaborator_threshold": COLLABORATOR_THRESHOLD,
        "contributions": contributions,
        "totals": people,
    }


def run_json(command: list[str]) -> Any:
    completed = subprocess.run(
        command, check=True, capture_output=True, text=True, encoding="utf-8"
    )
    return json.loads(completed.stdout)


def fetch_repository(repo: str) -> tuple[list[Any], list[Any], dict[int, list[Any]]]:
    issue_fields = ",".join(
        [
            "number",
            "title",
            "state",
            "stateReason",
            "assignees",
            "closedAt",
            "closedByPullRequestsReferences",
            "url",
        ]
    )
    issues = run_json(
        [
            "gh",
            "issue",
            "list",
            "--repo",
            repo,
            "--state",
            "all",
            "--limit",
            "1000",
            "--json",
            issue_fields,
        ]
    )
    pull_requests = run_json(
        [
            "gh",
            "pr",
            "list",
            "--repo",
            repo,
            "--state",
            "merged",
            "--limit",
            "1000",
            "--json",
            "number,title,author,mergedAt,url",
        ]
    )
    events_by_issue: dict[int, list[Any]] = {}
    for issue in issues:
        if parse_points(issue["title"]) is None or not issue["assignees"]:
            continue
        pages = run_json(
            [
                "gh",
                "api",
                "--paginate",
                "--slurp",
                f"repos/{repo}/issues/{issue['number']}/events?per_page=100",
            ]
        )
        events_by_issue[issue["number"]] = [event for page in pages for event in page]
    return issues, pull_requests, events_by_issue


def render_markdown(ledger: dict[str, Any]) -> str:
    lines = [
        "# Contribution score",
        "",
        "This public ledger is rebuilt from GitHub once per day. Do not edit the "
        "totals by hand. / 本公开账本每天从 GitHub 自动重建，请勿手工修改总分。",
        "",
        "## How it works / 计分规则",
        "",
        "- Choose an open issue whose title starts with `[N points]`, then comment "
        "`/claim`. One person gets 168 hours to merge a PR that closes it. / 选择标题以 "
        "`[N points]` 开头的 issue，评论 `/claim`；每次一人，须在 168 小时内合并关闭它的 PR。",
        "- A bug is at least 2 points, a new real use case is 3, and complex UI work "
        "is 12. Other scores are fixed before assignment. / bug 最低 2 分，新的真实使用案例 "
        "3 分，复杂 UI 工作 12 分；其他任务在认领前定分。",
        "- Six points earns a collaborator seat. Technical-report coauthorship also "
        "requires substantive intellectual contribution, drafting or critical revision, "
        "final approval, and accountability. / 累计 6 分获得协作者席位；"
        "技术报告署名还要求实质性智力贡献、撰写或关键修订、最终批准和责任承担。",
        "",
        "[Available scored issues](https://github.com/ktwu01/benchmark-radar/"
        "issues?q=is%3Aissue%20state%3Aopen%20%22points%5D%22) · "
        "[Propose a real use case](https://github.com/ktwu01/benchmark-radar/"
        "issues/new?template=use-case.yml) · "
        "[Full collaboration call](https://github.com/ktwu01/benchmark-radar/issues/447)",
        "",
        "## Totals / 总分",
        "",
        "| Contributor | Points | Collaborator seat |",
        "|---|---:|:---:|",
    ]
    for row in ledger["totals"]:
        eligible = "yes" if row["eligible_for_collaborator_seat"] else "no"
        lines.append(f"| @{row['contributor']} | {row['points']} | {eligible} |")
    if not ledger["totals"]:
        lines.append("| — | 0 | no |")

    active = [
        record
        for record in ledger["contributions"]
        if record["kind"] == "issue" and record["status"] == "active"
    ]
    if active:
        lines.extend(
            [
                "",
                "## Active claims / 进行中的认领",
                "",
                "| Issue | Contributor | Deadline | Points |",
                "|---|---|---|---:|",
            ]
        )
        for record in active:
            lines.append(
                f"| [#{record['number']}]({record['url']}) | "
                f"@{record['contributor']} | {record['deadline']} | {record['points']} |"
            )

    earned = [record for record in ledger["contributions"] if record["status"] == "earned"]
    lines.extend(
        [
            "",
            "## Earned points / 得分记录",
            "",
            "| Work | Contributor | Points |",
            "|---|---|---:|",
        ]
    )
    for record in earned:
        contributor = record["contributor"]
        work_type = "Issue" if record["kind"] == "issue" else "PR"
        label = f"[{work_type} #{record['number']}]({record['url']})"
        lines.append(f"| {label} | @{contributor} | {record['earned_points']} |")
    if not earned:
        lines.append("| — | — | 0 |")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo", default=os.environ.get("GITHUB_REPOSITORY", "ktwu01/benchmark-radar")
    )
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    args = parser.parse_args()
    issues, pull_requests, events = fetch_repository(args.repo)
    ledger = build_ledger(issues, pull_requests, events)
    if args.format == "json":
        print(json.dumps(ledger, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(ledger), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
