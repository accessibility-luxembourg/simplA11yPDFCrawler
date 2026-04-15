from pathlib import Path

from pikepdf import Pdf

from scanner.check_figures import check_figures
from scanner.checks import check_tagging
from scanner.image_detection import detect_image_objects
from scanner.structure import load_structure_items


FIXTURE_SUBDIR = "figures"


def open_pdf(path: Path) -> Pdf:
    return Pdf.open(str(path))


def build_figure_inputs(pdf: Pdf, result: dict):
    check_tagging(pdf, result)

    structure_items = []
    if pdf.Root.get("/StructTreeRoot") is not None:
        structure_items = load_structure_items(pdf)

    image_info = detect_image_objects(pdf)
    return structure_items, image_info


def test_figures_check_passes_for_tagged_pdf_with_no_figures(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "figures_tagged_no_figures_pass.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items, image_info = build_figure_inputs(pdf, result)
        check_figures(structure_items, result, image_info=image_info)

    assert result["TaggedTest"] == "Pass"
    assert result["FiguresFound"] == 0
    assert result["FiguresAltTextTest"] == "Pass"
    assert result["FiguresWithAlt"] == 0
    assert result["FiguresWithActualTextOnly"] == 0
    assert result["FiguresWithoutAlt"] == 0


def test_figures_check_passes_for_tagged_pdf_with_figure_alt_text(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "figures_tagged_alt_pass.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items, image_info = build_figure_inputs(pdf, result)
        check_figures(structure_items, result, image_info=image_info)

    assert result["TaggedTest"] == "Pass"
    assert result["FiguresFound"] == 1
    assert result["FiguresWithAlt"] == 1
    assert result["FiguresWithActualTextOnly"] == 0
    assert result["FiguresWithoutAlt"] == 0
    assert result["FiguresAltTextTest"] == "Pass"


def test_figures_check_warns_for_tagged_pdf_with_actualtext_only(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "figures_tagged_actualtext_warn.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items, image_info = build_figure_inputs(pdf, result)
        check_figures(structure_items, result, image_info=image_info)

    assert result["TaggedTest"] == "Pass"
    assert result["FiguresFound"] == 1
    assert result["FiguresWithActualTextOnly"] == 1
    assert result["FiguresWithoutAlt"] == 0
    assert result["FiguresAltTextTest"] == "Warn"
    assert "figures-actualtext" in result["_log"]


def test_figures_check_fails_for_tagged_pdf_with_figure_missing_alt_text(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "figures_tagged_no_alt_fail.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items, image_info = build_figure_inputs(pdf, result)
        check_figures(structure_items, result, image_info=image_info)

    assert result["TaggedTest"] == "Pass"
    assert result["FiguresFound"] == 1
    assert result["FiguresWithoutAlt"] == 1
    assert result["FiguresAltTextTest"] == "Fail"
    assert result["Accessible"] is False
    assert "figures-alt" in result["_log"]


def test_figures_check_fails_for_untagged_pdf_with_image(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "figures_untagged_images_fail.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items, image_info = build_figure_inputs(pdf, result)
        check_figures(structure_items, result, image_info=image_info)

    assert result["TaggedTest"] == "Fail"
    assert result["ImageObjectsFound"] == 1
    assert result["FiguresFound"] == 0
    assert result["FiguresAltTextTest"] == "Fail"
    assert result["Accessible"] is False
    assert "untagged-images" in result["_log"]


def test_figures_check_is_not_applicable_for_untagged_pdf_without_image(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "figures_untagged_no_images_na.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items, image_info = build_figure_inputs(pdf, result)
        check_figures(structure_items, result, image_info=image_info)

    assert result["TaggedTest"] == "Fail"
    assert result["ImageObjectsFound"] == 0
    assert result["FiguresFound"] == 0
    assert result["FiguresAltTextTest"] == "NotApplicable"


def test_figures_check_fails_for_scanned_image_only_pdf(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / "empty_text" / "empty_text_image_only_fail.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items, image_info = build_figure_inputs(pdf, result)
        check_figures(structure_items, result, image_info=image_info)

    assert result["TaggedTest"] == "Fail"
    assert result["ImageObjectsFound"] == 1
    assert result["FiguresFound"] == 0
    assert result["FiguresAltTextTest"] == "Fail"
    assert result["Accessible"] is False
    assert "untagged-images" in result["_log"]
