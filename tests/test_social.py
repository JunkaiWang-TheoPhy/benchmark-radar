import json
from pathlib import Path

from benchmark_radar import cli
from benchmark_radar.social import (
    SECTION_HEADING,
    GitChange,
    build_insight_sentence,
    extract_checked,
    load_channels,
    merge_checked,
    parse_git_log,
    render_social_section,
    summarize_repo_changes,
)


def test_insight_sentence_names_the_top_signal():
    items = [
        {
            "title": "A/Bench",
            "source": "GitHub",
            "total_score": 40.0,
            "score_max": 100.0,
        },
        {
            "title": "Top | Signal",
            "source": "Hugging Face",
            "total_score": 72.4,
            "score_max": 100.0,
        },
    ]
    sentence = build_insight_sentence(items)
    assert "2 items across GitHub, Hugging Face" in sentence
    assert "Top | Signal" in sentence
    assert "Hugging Face, 72/100" in sentence


def test_insight_sentence_empty():
    assert "no new" in build_insight_sentence([])


def test_repo_sentence_empty():
    sentence, highlights = summarize_repo_changes([])
    assert sentence == "No code changes in the last 24 hours."
    assert highlights == []


def test_repo_sentence_names_areas_by_human_labels():
    changes = [
        GitChange("Fix classifier", ("src/benchmark_radar/cli.py", "tests/test_cli.py")),
        GitChange("Add feeds", ("data/model_cards.yml", "site/data/radar.json")),
    ]
    sentence, _ = summarize_repo_changes(changes)
    assert sentence.startswith("2 commits in the last 24 hours")
    assert "radar code" in sentence
    assert "registry data" in sentence
    assert "tests" in sentence


def test_repo_sentence_hides_automated_and_merge_subjects_from_highlights():
    changes = [
        GitChange("Record daily radar snapshot", ("data/snapshots/2026-08-10.json",)),
        GitChange("Merge pull request #177", ()),
        GitChange("Fix source labeling", ("src/benchmark_radar/sources.py",)),
    ]
    sentence, highlights = summarize_repo_changes(changes)
    assert sentence.startswith("3 commits")
    assert highlights == ["Fix source labeling"]


def test_parse_git_log_handles_commit_blocks():
    text = (
        "abc123\0Record daily radar snapshot\n"
        "data/snapshots/2026-08-10.json\n"
        "\n"
        "def456\0Fix the classifier\n"
        "src/benchmark_radar/cli.py\n"
        "tests/test_cli.py\n"
        "\n"
    )
    changes = parse_git_log(text)
    assert changes == [
        GitChange("Record daily radar snapshot", ("data/snapshots/2026-08-10.json",)),
        GitChange("Fix the classifier", ("src/benchmark_radar/cli.py", "tests/test_cli.py")),
    ]


def test_parse_git_log_ties_files_to_the_right_commit_when_blank_precedes_files():
    # Real `git log --name-only` output places the blank separator before the
    # file list and emits nothing but the header for a no-diff merge commit.
    # Files must land on the commit whose header they follow, not the previous
    # one, or the repo-change sentence loses every area.
    text = (
        "abc123\0Merge pull request #1\n"
        "def456\0Fix the classifier\n"
        "\n"
        "src/benchmark_radar/cli.py\n"
        "ghi789\0Record daily radar snapshot\n"
        "\n"
        "data/snapshots/2026-08-10.json\n"
    )
    assert parse_git_log(text) == [
        GitChange("Merge pull request #1", ()),
        GitChange("Fix the classifier", ("src/benchmark_radar/cli.py",)),
        GitChange("Record daily radar snapshot", ("data/snapshots/2026-08-10.json",)),
    ]


def test_render_section_lists_every_channel_unchecked(tmp_path: Path):
    channels_path = tmp_path / "social.yml"
    channels_path.write_text(
        "social:\n  channels:\n    - name: X / Twitter\n    - name: 知乎\n",
        encoding="utf-8",
    )
    section = render_social_section(
        "insight",
        "repo change",
        [],
        load_channels(channels_path),
    )
    assert SECTION_HEADING in section
    assert "**Benchmark update:** insight" in section
    assert "**Repo change:** repo change" in section
    assert "- [ ] X / Twitter" in section
    assert "- [ ] 知乎" in section
    assert "- [x]" not in section


def test_merge_checked_keeps_prior_ticks_and_leaves_new_channels_unchecked():
    section = render_social_section(
        "insight",
        "repo change",
        [],
        [
            {"name": "X / Twitter"},
            {"name": "LinkedIn"},
            {"name": "知乎"},
        ],
    )
    existing = (
        "# 📡 AI Benchmark & Data Radar\n\n"
        "## 🗣 Daily social post\n\n"
        "- [x] LinkedIn\n"
        "- [ ] X / Twitter\n"
    )
    merged = merge_checked(section, existing)
    assert "- [x] LinkedIn" in merged
    assert "- [ ] X / Twitter" in merged
    assert "- [ ] 知乎" in merged


def test_extract_checked_only_reads_the_social_section():
    body = (
        "## At a glance\n\n- [x] Some checklist elsewhere\n\n"
        "## 🗣 Daily social post\n\n"
        "- [x] LinkedIn\n- [ ] X / Twitter\n"
    )
    assert extract_checked(body) == {"LinkedIn"}


def test_social_command_writes_section(monkeypatch, tmp_path: Path):
    items_path = tmp_path / "items.json"
    items_path.write_text(
        json.dumps(
            {
                "evidence_items": [
                    {
                        "title": "A/Bench",
                        "source": "GitHub",
                        "total_score": 55.0,
                        "score_max": 100.0,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    channels_path = tmp_path / "social.yml"
    channels_path.write_text(
        "social:\n  channels:\n    - name: X / Twitter\n    - name: LinkedIn\n",
        encoding="utf-8",
    )
    output = tmp_path / "social.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "benchmark-radar",
            "social",
            "--items",
            str(items_path),
            "--channels",
            str(channels_path),
            "--social-output",
            str(output),
        ],
    )
    cli.main()
    body = output.read_text(encoding="utf-8")
    assert SECTION_HEADING in body
    assert "1 item across GitHub" in body
    assert "- [ ] X / Twitter" in body
