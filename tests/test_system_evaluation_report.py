from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

SCRIPT_PATH = Path("scripts/build_system_evaluation.py")


class _FakeParagraph:
    def __init__(self, text, style=None):
        self.text = text
        self.style = style


class _FakeTable:
    def __init__(self, rows, **kwargs):
        self._cellvalues = rows
        self.kwargs = kwargs


class _FakeTableStyle:
    def __init__(self, commands):
        self.commands = commands


class _FakeSpacer:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class _FakePageBreak:
    pass


class _FakeParagraphStyle:
    def __init__(self, name, parent=None, **kwargs):
        self.name = name
        self.parent = parent
        self.kwargs = kwargs


class _FakeDrawing:
    def __init__(self, *args, **kwargs):
        self.items = []

    def add(self, item):
        self.items.append(item)


class _FakeShape:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class _FakeBaseDocTemplate:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def addPageTemplates(self, templates):
        self.templates = templates

    def build(self, story):
        self.story = story


class _FakeFrame:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class _FakePageTemplate:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


def _install_report_builder_stubs():
    fake_build = types.ModuleType("build_technical_report")
    fake_build.AMBER = "#AMBER"
    fake_build.BLUE = "#BLUE"
    fake_build.BOLD = "BOLD"
    fake_build.INK = "#INK"
    fake_build.ITALIC = "ITALIC"
    fake_build.MARGIN_X = 36
    fake_build.MUTED = "#MUTED"
    fake_build.NAVY = "#NAVY"
    fake_build.PAGE_W = 612
    fake_build.PALE_AMBER = "#PALE_AMBER"
    fake_build.PALE_TEAL = "#PALE_TEAL"
    fake_build.REGULAR = "REGULAR"
    fake_build.RULE = "#RULE"
    fake_build.SKY = "#SKY"
    fake_build.TEAL = "#TEAL"
    fake_build.WHITE = "#WHITE"
    fake_build.bullet = lambda text, style: _FakeParagraph(text, style)
    fake_build.p = lambda text, style: _FakeParagraph(text, style)
    fake_build.styles = lambda: {
        key: key
        for key in (
            "small",
            "meta",
            "title",
            "subtitle",
            "author",
            "callout",
            "section",
            "subsection",
            "body",
            "table_header",
            "small_bold",
            "metric",
            "metric_label",
            "reference",
        )
    }
    sys.modules["build_technical_report"] = fake_build

    reportlab = types.ModuleType("reportlab")
    graphics = types.ModuleType("reportlab.graphics")
    shapes = types.ModuleType("reportlab.graphics.shapes")
    shapes.Drawing = _FakeDrawing
    shapes.Line = _FakeShape
    shapes.Polygon = _FakeShape
    shapes.Rect = _FakeShape
    shapes.String = _FakeShape
    lib = types.ModuleType("reportlab.lib")
    colors = types.ModuleType("reportlab.lib.colors")
    colors.HexColor = lambda value: value
    pagesizes = types.ModuleType("reportlab.lib.pagesizes")
    pagesizes.letter = (612, 792)
    styles = types.ModuleType("reportlab.lib.styles")
    styles.ParagraphStyle = _FakeParagraphStyle
    units = types.ModuleType("reportlab.lib.units")
    units.inch = 72
    platypus = types.ModuleType("reportlab.platypus")
    platypus.BaseDocTemplate = _FakeBaseDocTemplate
    platypus.Frame = _FakeFrame
    platypus.PageBreak = _FakePageBreak
    platypus.PageTemplate = _FakePageTemplate
    platypus.Spacer = _FakeSpacer
    platypus.Table = _FakeTable
    platypus.TableStyle = _FakeTableStyle

    sys.modules["reportlab"] = reportlab
    sys.modules["reportlab.graphics"] = graphics
    sys.modules["reportlab.graphics.shapes"] = shapes
    sys.modules["reportlab.lib"] = lib
    sys.modules["reportlab.lib.colors"] = colors
    sys.modules["reportlab.lib.pagesizes"] = pagesizes
    sys.modules["reportlab.lib.styles"] = styles
    sys.modules["reportlab.lib.units"] = units
    sys.modules["reportlab.platypus"] = platypus


def _load_module():
    assert SCRIPT_PATH.exists(), f"missing report builder: {SCRIPT_PATH}"
    _install_report_builder_stubs()
    spec = importlib.util.spec_from_file_location("build_system_evaluation", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _collect_text(node) -> list[str]:
    if isinstance(node, _FakeParagraph):
        return [node.text]
    if isinstance(node, _FakeTable):
        texts: list[str] = []
        for row in node._cellvalues:
            for cell in row:
                texts.extend(_collect_text(cell))
        return texts
    if isinstance(node, list):
        texts: list[str] = []
        for item in node:
            texts.extend(_collect_text(item))
        return texts
    return []


def test_default_output_targets_next_draft():
    module = _load_module()

    args = module.build_parser().parse_args([])

    assert args.output == Path("output/pdf/benchmark-radar-technical-report-next-draft.pdf")
    assert args.output.name != "benchmark-radar-technical-report-v0.9.0.pdf"


def test_agent_weakness_section_reports_bounded_result_and_method():
    module = _load_module()

    report_data = module.load_agent_weakness_report_data()
    paragraphs = module.agent_weakness_section_paragraphs(report_data)
    section_text = "\n".join(paragraphs)

    assert report_data["issue_number"] == 455
    assert (
        report_data["issue_url"] == "https://github.com/ktwu01/benchmark-radar/issues/455"
    )
    assert report_data["contributor"] == "Junkai Wang / @JunkaiWang-TheoPhy"
    assert report_data["snapshot_date"] == "2026-09-01"
    assert report_data["evidence_cutoff"] == "2026-09-01"
    assert (
        report_data["repository_commit_input"]
        == "98c8cf6fb5d1d69c66d438ea9f92242b2205c9ae"
    )
    assert report_data["demonstrated_family_count"] == 9
    assert report_data["state_control_count"] == 7
    assert report_data["decision_execution_count"] == 2
    assert report_data["completed_secondary_review_count"] == 4
    assert report_data["sampled_secondary_review_count"] == 4
    assert report_data["design_implied_count"] == 1
    assert report_data["unmeasured_count"] == 1
    assert report_data["measurement_counterexample_only"] == ["SciCode"]

    assert paragraphs[0].startswith("Across 9 demonstrated benchmark families")
    assert "family-deduplicated denominator" in section_text
    assert "7/9" in section_text
    assert "state-control" in section_text
    assert "2/9" in section_text
    assert "decision-execution" in section_text
    assert "selected sample" in section_text
    assert "not a field-wide prevalence estimate" in section_text
    assert "Junkai Wang / @JunkaiWang-TheoPhy" in section_text
    assert "https://github.com/ktwu01/benchmark-radar/issues/455" in section_text
    assert "2026-09-01" in section_text
    assert "98c8cf6fb5d1d69c66d438ea9f92242b2205c9ae" in section_text
    assert "demonstrated" in section_text
    assert "design-implied" in section_text
    assert "unmeasured" in section_text
    assert "4/4" in section_text
    assert "does not establish broad reliability" in section_text
    assert "SciCode" in section_text
    assert "instrument counterexample" in section_text
    assert "measurement implications and limits" in section_text.lower()


def test_story_places_agent_weakness_subsection_before_use_it_and_adds_primary_sources():
    module = _load_module()

    texts = _collect_text(module.story("10.5281/zenodo.22167102"))

    subsection_index = texts.index("6.5 Selected benchmark-family signal on agent weaknesses")
    use_it_index = texts.index("Use it")
    refs_index = texts.index(
        "[9] Primary-source evidence for OSWorld 2.0. https://arxiv.org/html/2606.29537v1"
    )

    assert subsection_index < use_it_index
    assert refs_index > texts.index("References")
    assert (
        "[18] Primary-source evidence for SciCode. https://arxiv.org/abs/2608.04975"
        in texts
    )
