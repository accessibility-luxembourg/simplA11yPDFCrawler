from pathlib import Path

from pikepdf import Pdf

from scanner.checks.lists import check_lists
from scanner.checks.document import check_tagging
from scanner.structure import load_structure_items


FIXTURE_SUBDIR = "lists"


def open_pdf(path: Path) -> Pdf:
    return Pdf.open(str(path))


def build_list_inputs(pdf: Pdf, result: dict):
    check_tagging(pdf, result)

    structure_items = []
    if pdf.Root.get("/StructTreeRoot") is not None:
        structure_items = load_structure_items(pdf)

    return structure_items


def test_lists_check_passes_for_tagged_pdf_with_simple_list(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "lists_simple_pass.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_list_inputs(pdf, result)
        check_lists(structure_items, result)

    print("Malformed", result["MalformedListNodes"])
    print("InvalidListItemParents", result["InvalidListItemParents"])
    print("InvalidListChildren", result["InvalidListChildren"])
    assert result["TaggedTest"] == "Pass"
    assert result["ListCount"] == 1
    assert result["ListsTest"] == "Pass"
    assert result["Accessible"] is True
    assert result["InvalidListItemParents"] == ""
    assert result["InvalidListChildren"] == ""
    assert result["MalformedListNodes"] == ""


# Tests for this L > LI > LBody > L
# This is how HTML works and seems the most sensible to me
def test_lists_check_passes_for_tagged_pdf_with_nested_list_inside_lbody(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "lists_nested_in_lbody_pass.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_list_inputs(pdf, result)
        check_lists(structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["ListCount"] >= 2
    assert result["ListsTest"] == "Pass"
    assert result["Accessible"] is True
    assert result["InvalidListItemParents"] == ""
    assert result["InvalidListChildren"] == ""
    assert result["MalformedListNodes"] == ""


# Tests for this L > L
# The spec calls this out as an allowed structure
def test_lists_check_passes_for_tagged_pdf_with_hierarchical_nested_list_directly_under_l(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "lists_nested_direct_under_l_pass.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_list_inputs(pdf, result)
        check_lists(structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["ListCount"] >= 2
    assert result["ListsTest"] == "Pass"
    assert result["Accessible"] is True
    assert result["InvalidListItemParents"] == ""
    assert result["InvalidListChildren"] == ""
    assert result["MalformedListNodes"] == ""


# Tests for this L > Div > L
# The spec calls this out as an allowed structure
def test_lists_check_passes_for_tagged_pdf_with_hierarchical_nested_list_inside_div(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "lists_nested_inside_div_pass.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_list_inputs(pdf, result)
        check_lists(structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["ListCount"] >= 2
    assert result["ListsTest"] == "Pass"
    assert result["Accessible"] is True
    assert result["InvalidListItemParents"] == ""
    assert result["InvalidListChildren"] == ""
    assert result["MalformedListNodes"] == ""


def test_lists_check_passes_for_tagged_pdf_with_missing_lbl_only(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "lists_missing_lbl_only_pass.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_list_inputs(pdf, result)
        check_lists(structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["ListCount"] >= 1
    assert result["ListsTest"] == "Pass"
    assert result["Accessible"] is True
    assert result["InvalidListItemParents"] == ""
    assert result["InvalidListChildren"] == ""
    assert result["MalformedListNodes"] == ""


def test_lists_check_warns_when_li_is_missing_lbody(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "lists_missing_lbody_warn.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_list_inputs(pdf, result)
        check_lists(structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["ListsTest"] == "Warn"
    assert result["Accessible"] is True
    assert "missing LBody" in result["MalformedListNodes"]
    assert "lists-warn" in result["_log"]


# Tests for this L > LI > LBody [empty]
def test_lists_check_warns_for_empty_lbody(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "lists_empty_lbody_warn.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_list_inputs(pdf, result)
        check_lists(structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["ListsTest"] == "Warn"
    assert result["Accessible"] is True
    assert "LBody is empty" in result["MalformedListNodes"]
    assert "lists-warn" in result["_log"]


# Tests for this L > LI > P > "Hello"
# The P tag should be inside of an LBody tag
def test_lists_check_warns_for_li_with_direct_content_children(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "lists_direct_content_children_warn.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_list_inputs(pdf, result)
        check_lists(structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["ListsTest"] == "Warn"
    assert result["Accessible"] is True
    assert result["InvalidListItemParents"] == ""
    assert result["InvalidListChildren"] != ""
    assert "LI has unusual children Span, P" in result["InvalidListChildren"]
    assert "missing LBody but contains direct content" in result["MalformedListNodes"]
    assert "lists-warn" in result["_log"]


# Tests for this L > LI > [Lbl, LBody, P]
# In this case, "P" should not be there, it should be inside of LBody
def test_lists_check_warns_for_li_with_extra_direct_children(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "lists_extra_direct_children_warn.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_list_inputs(pdf, result)
        check_lists(structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["ListsTest"] == "Warn"
    assert result["Accessible"] is True
    assert result["InvalidListItemParents"] == ""
    assert result["InvalidListChildren"] != ""
    assert "unusual children" in result["InvalidListChildren"]
    assert "P" in result["InvalidListChildren"]  # we know there are "P" tags in there
    assert "missing LBody" not in result["MalformedListNodes"]
    assert "lists-warn" in result["_log"]


# Tests for this L > LI > "Hello"
# The text content should be inside of an LBody tag
def test_lists_check_warns_for_li_with_direct_content_and_no_child_tags(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "lists_direct_content_no_tags_warn.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_list_inputs(pdf, result)
        check_lists(structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["ListsTest"] == "Warn"
    assert result["Accessible"] is True
    assert result["InvalidListItemParents"] == ""
    assert result["InvalidListChildren"] == ""
    assert "missing LBody but contains direct content" in result["MalformedListNodes"]
    assert "lists-warn" in result["_log"]


# Tests for this L > LI [empty]
def test_lists_check_warns_for_empty_li(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "lists_empty_li_warn.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_list_inputs(pdf, result)
        check_lists(structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["ListCount"] >= 1
    assert result["ListsTest"] == "Warn"
    assert result["Accessible"] is True
    assert "LI is empty" in result["MalformedListNodes"]
    assert "lists-warn" in result["_log"]


# Tests for this L [empty]
def test_lists_check_warns_for_empty_l(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "lists_empty_l_warn.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_list_inputs(pdf, result)
        check_lists(structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["ListCount"] >= 1
    assert result["ListsTest"] == "Warn"
    assert result["Accessible"] is True
    assert "L is empty" in result["MalformedListNodes"]
    assert "lists-warn" in result["_log"]


# Tests for this Div > LI
# "LI" tags should be inside of an "L" tag
def test_lists_check_fails_when_li_parent_is_not_l(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "lists_li_wrong_parent_fail.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_list_inputs(pdf, result)
        check_lists(structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["ListsTest"] == "Fail"
    assert result["Accessible"] is False
    assert "LI parent is Div, expected L" in result["InvalidListItemParents"]
    assert "lists-fail" in result["_log"]


# Tests for this L > P > [Lbl, LBody]
# We should have "LI" tags under the "L" tag
def test_lists_check_fails_when_lbody_parent_is_not_li(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "lists_lbody_wrong_parent_fail.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_list_inputs(pdf, result)
        check_lists(structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["ListsTest"] == "Fail"
    assert result["Accessible"] is False
    assert "LBody parent is P, expected LI" in result["MalformedListNodes"]
    assert "lists-fail" in result["_log"]


# Tests for this L > P > LBody
# This is the inverse of the test above, checking the LBody parent rather than the L's children
def test_lists_check_fails_when_l_has_disallowed_direct_children(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "lists_l_disallowed_child_fail.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_list_inputs(pdf, result)
        check_lists(structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["ListsTest"] == "Fail"
    assert result["Accessible"] is False
    assert "L has disallowed children P, P, P" in result["MalformedListNodes"]
    assert "lists-fail" in result["_log"]


def test_lists_check_is_not_applicable_for_tagged_pdf_with_no_lists(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "lists_none_na.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_list_inputs(pdf, result)
        check_lists(structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["ListCount"] == 0
    assert result["InvalidListItemParents"] == ""
    assert result["InvalidListChildren"] == ""
    assert result["MalformedListNodes"] == ""
    assert result["ListsTest"] == "NotApplicable"
    assert result["Accessible"] is True


def test_lists_check_is_not_applicable_for_untagged_pdf(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "lists_untagged_na.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_list_inputs(pdf, result)
        check_lists(structure_items, result)

    assert result["TaggedTest"] == "Fail"
    assert result["ListCount"] == 0
    assert result["InvalidListItemParents"] == ""
    assert result["InvalidListChildren"] == ""
    assert result["MalformedListNodes"] == ""
    assert result["ListsTest"] == "NotApplicable"
