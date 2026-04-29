from pathlib import Path

from pikepdf import Pdf

from scanner.check_alt_text import check_nested_alt_text
from scanner.checks import check_tagging
from scanner.structure import load_structure_items


FIXTURE_SUBDIR = "alt_text"


def open_pdf(path: Path) -> Pdf:
    return Pdf.open(str(path))


def build_alt_text_inputs(pdf: Pdf, result: dict):
    check_tagging(pdf, result)

    structure_items = []
    if pdf.Root.get("/StructTreeRoot") is not None:
        structure_items = load_structure_items(pdf)

    return structure_items


# Untagged PDF: nested alt text check is not applicable
def test_nested_alt_text_is_not_applicable_for_untagged_pdf(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "alt_text_untagged_na.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_alt_text_inputs(pdf, result)
        check_nested_alt_text(structure_items, result)

    assert result["TaggedTest"] == "Fail"
    assert result["NestedAltTextTest"] == "NotApplicable"
    assert result["NestedAltTextIssues"] == ""


# Tagged PDF with no alt-bearing structure items: nested alt text check is not applicable
def test_nested_alt_text_is_not_applicable_when_no_alt_text_exists(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "alt_text_none_na.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_alt_text_inputs(pdf, result)
        check_nested_alt_text(structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["NestedAltTextTest"] == "NotApplicable"
    assert result["NestedAltTextIssues"] == ""
    assert result["Accessible"] is True


# Tagged PDF with one alt-bearing structure item and no nested alt descendants: pass
def test_nested_alt_text_passes_when_alt_text_is_not_nested(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "alt_text_single_alt_pass.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_alt_text_inputs(pdf, result)
        check_nested_alt_text(structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["NestedAltTextTest"] == "Pass"
    assert result["NestedAltTextIssues"] == ""
    assert result["Accessible"] is True


# Tagged PDF with an alt-bearing structure item nested inside another alt-bearing subtree: fail
def test_nested_alt_text_fails_when_alt_text_is_nested(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "alt_text_nested_fail.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_alt_text_inputs(pdf, result)
        check_nested_alt_text(structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["NestedAltTextTest"] == "Fail"
    assert result["NestedAltTextIssues"] != ""
    assert "nested inside" in result["NestedAltTextIssues"]
    assert result["Accessible"] is False
    assert "alt-nested-fail" in result["_log"]


# Tagged PDF with an alt-bearing structure item nested several levels deep
# inside another alt-bearing subtree: fail
def test_nested_alt_text_fails_when_alt_text_is_nested_deeply(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "alt_text_nested_deep_fail.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_alt_text_inputs(pdf, result)
        check_nested_alt_text(structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["NestedAltTextTest"] == "Fail"
    assert result["NestedAltTextIssues"] != ""
    assert "nested inside" in result["NestedAltTextIssues"]
    assert result["Accessible"] is False
    assert "alt-nested-fail" in result["_log"]


# Tagged PDF with two alt-bearing descendants nested under one alt-bearing
# ancestor: fail and report multiple issues
def test_nested_alt_text_fails_when_multiple_nested_alt_descendants_exist(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = (
        fixtures_dir / FIXTURE_SUBDIR / "alt_text_multiple_nested_descendants_fail.pdf"
    )
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_alt_text_inputs(pdf, result)
        check_nested_alt_text(structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["NestedAltTextTest"] == "Fail"
    assert result["NestedAltTextIssues"] != ""
    assert result["NestedAltTextIssues"].count("nested inside") >= 2
    assert result["Accessible"] is False
    assert "alt-nested-fail" in result["_log"]


# Tagged PDF with multiple alt-bearing sibling elements but no nesting: pass
def test_nested_alt_text_passes_for_multiple_alt_bearing_siblings(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "alt_text_sibling_alt_pass.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_alt_text_inputs(pdf, result)
        check_nested_alt_text(structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["NestedAltTextTest"] == "Pass"
    assert result["NestedAltTextIssues"] == ""
    assert result["Accessible"] is True
