import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from contributor_points import (  # noqa: E402
    build_ledger,
    evaluate_issue,
    parse_points,
    render_markdown,
)

START = datetime(2026, 8, 30, tzinfo=UTC)


def issue(**changes):
    value = {
        "number": 10,
        "title": "[12 points] Build the UI",
        "state": "CLOSED",
        "stateReason": "COMPLETED",
        "assignees": [{"login": "alice"}],
        "closedAt": "2026-09-06T00:00:00Z",
        "closedByPullRequestsReferences": [{"number": 20}],
        "url": "https://example.test/issues/10",
    }
    value.update(changes)
    return value


def pull_request(**changes):
    value = {
        "number": 20,
        "title": "Implement the UI",
        "author": {"login": "alice"},
        "mergedAt": "2026-09-06T00:00:00Z",
        "url": "https://example.test/pull/20",
    }
    value.update(changes)
    return value


def assigned(login="alice", at="2026-08-30T00:00:00Z"):
    return {"event": "assigned", "assignee": {"login": login}, "created_at": at}


def test_point_prefix_accepts_ui_scale_and_rejects_invalid_values():
    assert parse_points("[1 point] Fix one word") == 1
    assert parse_points("[2 points] Fix a bug") == 2
    assert parse_points("[12 points] Rebuild the UI") == 12
    assert parse_points("[125 points] Very large project") == 125
    assert parse_points("[0 points] Invalid") is None
    assert parse_points("12 points without brackets") is None


def test_issue_earns_all_points_at_the_exact_seven_day_boundary():
    record = evaluate_issue(issue(), {20: pull_request()}, [assigned()], policy_start=START)

    assert record["status"] == "earned"
    assert record["earned_points"] == 12


def test_issue_expires_one_second_after_seven_days():
    record = evaluate_issue(
        issue(closedAt="2026-09-06T00:00:01Z"),
        {20: pull_request(mergedAt="2026-09-06T00:00:01Z")},
        [assigned()],
        policy_start=START,
    )

    assert record["status"] == "expired"
    assert record["earned_points"] == 0


def test_open_claim_becomes_expired_and_multiple_assignees_are_invalid():
    expired = evaluate_issue(
        issue(state="OPEN", stateReason=None, closedAt=None),
        {},
        [assigned()],
        policy_start=START,
        now=datetime(2026, 9, 6, 0, 0, 1, tzinfo=UTC),
    )
    multiple = evaluate_issue(
        issue(assignees=[{"login": "alice"}, {"login": "bob"}]),
        {},
        [assigned()],
        policy_start=START,
    )

    assert expired["status"] == "expired"
    assert multiple["status"] == "invalid"


def test_completed_issue_requires_a_closing_pr_by_the_assignee():
    record = evaluate_issue(
        issue(),
        {20: pull_request(author={"login": "bob"})},
        [assigned()],
        policy_start=START,
    )

    assert record["status"] == "invalid"
    assert record["earned_points"] == 0


def test_historical_prs_count_once_and_bots_cannot_take_a_seat():
    historical = [
        pull_request(
            number=1,
            title="[4 points] Add evidence",
            mergedAt="2026-08-20T00:00:00Z",
        ),
        pull_request(
            number=2,
            title="[8 points] Add analysis",
            mergedAt="2026-08-21T00:00:00Z",
        ),
        pull_request(
            number=3,
            title="[12 points] Owner work",
            author={"login": "ktwu01"},
            mergedAt="2026-08-22T00:00:00Z",
        ),
        pull_request(
            number=4,
            title="[8 points] Dependency update",
            author={"login": "app/dependabot"},
            mergedAt="2026-08-23T00:00:00Z",
        ),
        pull_request(
            number=5,
            title="[10 points] Post-policy work",
            mergedAt="2026-09-01T00:00:00Z",
        ),
        pull_request(
            number=463,
            title="[3 points] Promised post-policy work",
            author={"login": "JiayuuWang"},
            mergedAt="2026-08-31T03:36:33Z",
        ),
        pull_request(
            number=472,
            title="[3 points] More promised post-policy work",
            author={"login": "JiayuuWang"},
            mergedAt="2026-08-31T14:52:17Z",
        ),
    ]

    ledger = build_ledger([], historical, {}, policy_start=START, now=START)
    totals = {row["contributor"]: row for row in ledger["totals"]}

    assert totals["alice"] == {
        "contributor": "alice",
        "points": 12,
        "eligible_for_collaborator_seat": True,
    }
    assert ledger["collaborator_threshold"] == 12
    assert totals["app/dependabot"]["points"] == 8
    assert not totals["app/dependabot"]["eligible_for_collaborator_seat"]
    assert totals["JiayuuWang"] == {
        "contributor": "JiayuuWang",
        "points": 6,
        "eligible_for_collaborator_seat": False,
    }
    assert "ktwu01" not in totals


def test_public_markdown_is_standalone_and_omits_unclaimed_queue():
    ledger = build_ledger(
        [issue(state="OPEN", stateReason=None, closedAt=None, assignees=[])],
        [
            pull_request(
                number=1,
                title="[2 points] Fix bug",
                mergedAt="2026-08-20T00:00:00Z",
            )
        ],
        {},
        policy_start=START,
        now=START,
    )

    markdown = render_markdown(ledger)

    assert markdown.startswith("# Contribution score\n")
    assert "`/claim`" in markdown
    assert "Only work an outside contributor can complete is scored" in markdown
    assert "clear model-card addition is 3 and a new real use case is 6" in markdown
    assert "[PR #1](https://example.test/pull/20)" in markdown
    assert "ready" not in markdown
