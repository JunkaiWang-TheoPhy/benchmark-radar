import ast
import json
import re
from pathlib import Path

REPORT_BUILDER = Path("scripts/build_system_evaluation.py")
REPORT_README = Path("docs/technical-report/README.md")
REPORT_NARRATIVE = Path("docs/technical-report/vendor-attention-audit.md")
CLAIM_AUDIT = Path("docs/technical-report/vendor-attention-audit/claim-audit.json")


def test_report_replaces_the_unreproducible_eight_benchmark_claim():
    source = REPORT_BUILDER.read_text(encoding="utf-8")

    assert "load_vendor_attention_report_data" in source
    assert "vendor_attention_section_paragraphs" in source
    assert "6.1 A recurring reporting group with a definition-sensitive boundary" in source
    assert "https://github.com/ktwu01/benchmark-radar/issues/456" in source
    assert "Junkai Wang / @JunkaiWang-TheoPhy" in source
    assert "Eight benchmarks appear in documents from at least six organizations" not in source
    assert "form the rest of the top eight" not in source


def test_report_build_instructions_regenerate_the_audit_and_next_draft():
    readme = REPORT_README.read_text(encoding="utf-8")

    assert "scripts/analyze_vendor_attention.py" in readme
    assert "data/vendor_attention_audit.yml" in readme
    assert "docs/technical-report/vendor-attention-audit/claim-audit.json" in readme
    assert "output/pdf/benchmark-radar-technical-report-next-draft.pdf" in readme
    assert "must not overwrite" in readme


def test_report_builder_defaults_to_the_next_draft_not_the_frozen_pdf():
    source = REPORT_BUILDER.read_text(encoding="utf-8")
    tree = ast.parse(source)
    path_literal = None
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == "NEXT_DRAFT_OUTPUT"
            for target in node.targets
        ):
            continue
        assert isinstance(node.value, ast.Call)
        assert isinstance(node.value.args[0], ast.Constant)
        path_literal = node.value.args[0].value

    assert path_literal == "output/pdf/benchmark-radar-technical-report-next-draft.pdf"
    assert "default=NEXT_DRAFT_OUTPUT" in source
    assert 'default=Path("output/pdf/benchmark-radar-technical-report-v0.9.0.pdf")' not in source


def test_report_narrative_carries_the_machine_readable_replacement_claim():
    narrative = re.sub(r"\s+", " ", REPORT_NARRATIVE.read_text(encoding="utf-8")).replace("> ", "")
    audit = json.loads(CLAIM_AUDIT.read_text(encoding="utf-8"))

    assert audit["replacement_claim"] in narrative
    assert "not_observed" in narrative
    assert "convenience sample" in narrative
    assert "Junkai Wang /" in narrative
    assert "issues/456" in narrative
