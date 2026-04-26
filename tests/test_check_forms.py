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
