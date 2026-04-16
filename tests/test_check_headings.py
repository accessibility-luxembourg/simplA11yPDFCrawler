from pathlib import Path

from pikepdf import Pdf

from scanner.check_headings import check_headings
from scanner.checks import check_tagging
from scanner.structure import load_structure_items


FIXTURE_SUBDIR = "headings"


def open_pdf(path: Path) -> Pdf:
    return Pdf.open(str(path))


def build_heading_inputs(pdf: Pdf, result: dict):
    check_tagging(pdf, result)

    structure_items = []
    if pdf.Root.get("/StructTreeRoot") is not None:
        structure_items = load_structure_items(pdf)

    return structure_items


def test_headings_check_passes_for_tagged_pdf_with_h1_h2_h3(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "headings_h1_h2_h3_pass.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_heading_inputs(pdf, result)
        check_headings(structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["HeadingCount"] == 3
    assert result["HeadingSequence"] == "H1 > H2 > H3"
    assert result["HeadingIssues"] == ""
    assert result["HeadingsTest"] == "Pass"
    assert result["Accessible"] is True


def test_headings_check_fails_for_tagged_pdf_with_skipped_heading_level(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "headings_h1_h3_fail.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_heading_inputs(pdf, result)
        check_headings(structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["HeadingCount"] == 2
    assert result["HeadingSequence"] == "H1 > H3"
    assert result["HeadingsTest"] == "Fail"
    assert result["Accessible"] is False
    assert "Skipped heading level" in result["HeadingIssues"]
    assert "headings-skip" in result["_log"]


def test_headings_check_warns_when_first_heading_is_h2(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "headings_first_h2_warn.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_heading_inputs(pdf, result)
        check_headings(structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["HeadingCount"] >= 1
    assert result["HeadingSequence"].startswith("H2")
    assert result["HeadingsTest"] == "Warn"
    assert result["Accessible"] is True
    assert "First known heading is H2, not H1" in result["HeadingIssues"]
    assert "headings-warn" in result["_log"]


def test_headings_check_warns_for_tagged_pdf_with_no_headings(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "headings_none_warn.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_heading_inputs(pdf, result)
        check_headings(structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["HeadingCount"] == 0
    assert result["HeadingSequence"] == ""
    assert result["HeadingsTest"] == "Warn"
    assert result["Accessible"] is True
    assert result["HeadingIssues"] == "No headings found in tagged document"
    assert "headings-none" in result["_log"]


def test_headings_check_is_not_applicable_for_untagged_pdf(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "headings_untagged_na.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_heading_inputs(pdf, result)
        check_headings(structure_items, result)

    assert result["TaggedTest"] == "Fail"
    assert result["HeadingCount"] == 0
    assert result["HeadingSequence"] == ""
    assert result["HeadingIssues"] == ""
    assert result["HeadingsTest"] == "NotApplicable"


def test_headings_check_warns_for_tagged_pdf_with_plain_h_tags(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "headings_plain_h_warn.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_heading_inputs(pdf, result)
        check_headings(structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["HeadingCount"] >= 1
    assert "H" in result["HeadingSequence"]
    assert result["HeadingsTest"] == "Warn"
    assert result["Accessible"] is True
    assert "Plain H tag encountered" in result["HeadingIssues"]
    assert "headings-warn" in result["_log"]
