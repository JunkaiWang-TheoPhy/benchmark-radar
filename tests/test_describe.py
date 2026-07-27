from benchmark_radar.describe import (
    clean_card_text,
    github_summary,
    huggingface_summary,
    strip_title_echo,
)


def test_card_text_is_stripped_of_markdown_and_front_matter():
    raw = "---\nlicense: mit\n---\n\n# Title\n\n[![badge](x.svg)](y) Real **prose** here."
    assert clean_card_text(raw) == "Title Real prose here."


def test_card_text_truncates_on_a_sentence_boundary():
    body = "First sentence is meaningful. " + "padding word " * 60
    result = clean_card_text(body)
    assert result.startswith("First sentence is meaningful.")
    assert len(result) <= 401


def test_empty_card_text_stays_empty():
    assert clean_card_text(None) == ""
    assert clean_card_text("   \n\t ") == ""
    assert clean_card_text("---\nlicense: mit\n---") == ""


def test_title_echo_is_dropped():
    assert strip_title_echo("my-benchmark", "org/my-benchmark") == ""
    assert strip_title_echo("my-benchmark: real detail", "org/my-benchmark") == "real detail"


def test_huggingface_uses_real_card_prose():
    row = {
        "description": "\n\t\n\tsc-splicing-benchmark\n\t\nMUSSEL scored against truth v4.",
        "cardData": {"license": "mit"},
    }
    assert huggingface_summary(row, "depinwang/sc-splicing-benchmark") == (
        "MUSSEL scored against truth v4."
    )


def test_huggingface_falls_back_to_declared_metadata():
    row = {
        "description": "",
        "cardData": {
            "task_categories": ["question-answering"],
            "size_categories": ["1K<n<10K"],
            "language": ["en"],
        },
        "tags": ["license:mit", "region:us", "benchmark", "medical"],
    }
    result = huggingface_summary(row, "org/thing")
    assert "tasks: question-answering" in result
    assert "size: 1K<n<10K" in result
    # Machine-generated namespaces and words the pills already show are excluded.
    assert "license:mit" not in result
    assert "region:us" not in result


def test_huggingface_returns_empty_when_source_published_nothing():
    """An unlabelled repo must not receive a generated description."""
    assert huggingface_summary({"description": "", "cardData": {}, "tags": []}, "org/bare") == ""
    assert huggingface_summary({}, "org/bare") == ""


def test_github_blank_description_is_not_filled():
    assert github_summary({"description": None}) == ""
    assert github_summary({"description": "A real blurb."}) == "A real blurb."
