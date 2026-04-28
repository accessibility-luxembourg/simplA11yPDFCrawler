from pathlib import Path

from pikepdf import Pdf

from scanner.check_forms import check_forms, check_form_fields
from scanner.checks import check_tagging
from scanner.structure import load_structure_items


FIXTURE_SUBDIR = "forms"


def open_pdf(path: Path) -> Pdf:
    return Pdf.open(str(path))


def build_form_inputs(pdf: Pdf, result: dict):
    check_tagging(pdf, result)

    structure_items = []
    if pdf.Root.get("/StructTreeRoot") is not None:
        structure_items = load_structure_items(pdf)

    return structure_items


# Tagged PDF with no forms (/AcroForm) at all: leave form-related fields unchanged
def test_check_forms_does_nothing_when_no_acroform(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "forms_none_na.pdf"
    result = make_result(pdf_path.name)
    original_exempt = result["Exempt"]

    with open_pdf(pdf_path) as pdf:
        check_forms(pdf, result)

    assert result["Form"] is None
    assert result["xfa"] is None
    assert result["Exempt"] == original_exempt
    assert result["Accessible"] is True


# Tagged PDF with at least one form (/AcroForm) and at least one field: mark as Form and clear Exempt
def test_check_forms_sets_form_true_for_acroform_with_fields(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "forms_acroform_fields_pass.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        check_forms(pdf, result)

    assert result["Form"] is True
    assert result["Exempt"] is False


# PDF with dynamic XFA config: set xfa=True and log the XFA finding
def test_check_forms_sets_xfa_true_for_dynamic_xfa_form(
    fixtures_dir: Path,
    make_result,
):
    # it is hard to make an XFA PDF, so I found one online:
    # tutorial here: https://kb.itextpdf.com/itext/xfa-examples
    # PDF form is here: https://github.com/itext/itext-publications-examples-java/blob/develop/src/main/resources/pdfs/purchase_order.pdf
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "purchase_order.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        check_forms(pdf, result)

    assert result["xfa"] is True
    assert "xfa" in result["_log"]


# PDF with no interactive fields: form field checks are not applicable
# Note that this reuses the same PDF from the first test "test_check_forms_does_nothing_when_no_acroform"
# This test is testing a different function however
def test_check_form_fields_is_not_applicable_when_no_interactive_fields(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "forms_none_na.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        check_forms(pdf, result)
        structure_items = build_form_inputs(pdf, result)
        check_form_fields(pdf, structure_items, result)

    assert result["FormFieldCount"] == 0
    assert result["FormsTest"] == "NotApplicable"
    assert result["TaggedFormFieldsTest"] == "NotApplicable"
    assert result["FieldsWithoutDescription"] == ""
    assert result["UnclearFieldAssociations"] == ""
    assert result["Accessible"] is True


# PDF with one interactive field and a description: pass field description check
def test_check_form_fields_passes_for_single_field_with_description(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "forms_single_field_description_pass.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        check_forms(pdf, result)
        structure_items = build_form_inputs(pdf, result)
        check_form_fields(pdf, structure_items, result)

    assert result["FormFieldCount"] == 1
    assert result["FormsTest"] == "Pass"
    assert result["FieldsWithoutDescription"] == ""
    assert result["Accessible"] is True


# PDF with one interactive field and no description: fail field description check
def test_check_form_fields_fails_for_single_field_no_description(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = (
        fixtures_dir / FIXTURE_SUBDIR / "forms_single_field_no_description_fail.pdf"
    )
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        check_forms(pdf, result)
        structure_items = build_form_inputs(pdf, result)
        check_form_fields(pdf, structure_items, result)

    assert result["FormFieldCount"] == 1
    assert result["FormsTest"] == "Fail"
    assert result["FieldsWithoutDescription"] != ""
    assert result["Accessible"] is False
    assert "forms-fail" in result["_log"]


# PDF with two interactive fields where only one has a description: fail and report only the missing one
def test_check_form_fields_fails_when_one_of_two_fields_lacks_description(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = (
        fixtures_dir / FIXTURE_SUBDIR / "forms_mixed_missing_description_fail.pdf"
    )
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        check_forms(pdf, result)
        structure_items = build_form_inputs(pdf, result)
        check_form_fields(pdf, structure_items, result)

    print(result["FieldsWithoutDescription"])
    assert result["FormFieldCount"] == 2
    assert result["FormsTest"] == "Fail"
    assert result["FieldsWithoutDescription"] != ""
    assert "missing description" in result["FieldsWithoutDescription"]
    assert result["Accessible"] is False
    assert "forms-fail" in result["_log"]


# Untagged PDF with an interactive field: fail tagged form fields check
def test_check_form_fields_fails_for_untagged_pdf_with_interactive_field(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "forms_untagged_field_fail.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        check_forms(pdf, result)
        structure_items = build_form_inputs(pdf, result)
        check_form_fields(pdf, structure_items, result)

    assert result["FormFieldCount"] >= 1
    assert result["TaggedTest"] == "Fail"
    assert result["TaggedFormFieldsTest"] == "Fail"
    assert result["Accessible"] is False
    assert "forms-untagged" in result["_log"]


# Tagged PDF with interactive field(s) but no Form structure elements: warn
def test_check_form_fields_warns_for_tagged_pdf_without_form_structure_elements(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "forms_tagged_no_form_struct_warn.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        check_forms(pdf, result)
        structure_items = build_form_inputs(pdf, result)
        check_form_fields(pdf, structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["FormFieldCount"] >= 1
    assert result["TaggedFormFieldsTest"] == "Warn"
    assert "forms-tagging-warn" in result["_log"]


# Tagged PDF with interactive field(s) and Form structure elements: pass
# Note that this is the same PDF used for test: "test_check_form_fields_passes_for_single_field_with_description"
def test_check_form_fields_passes_for_tagged_pdf_with_form_structure_elements(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "forms_single_field_description_pass.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        check_forms(pdf, result)
        structure_items = build_form_inputs(pdf, result)
        check_form_fields(pdf, structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["FormFieldCount"] >= 1
    assert result["TaggedFormFieldsTest"] == "Pass"
