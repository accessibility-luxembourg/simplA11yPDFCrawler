from pathlib import Path

from pikepdf import Pdf

from scanner.checks import check_empty_text


FIXTURE_SUBDIR = "empty_text"


def open_pdf(path: Path) -> Pdf:
    return Pdf.open(str(path))


def test_empty_text_check_passes_for_pdf_with_real_text(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "empty_text_pass.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        check_empty_text(pdf, result)

    assert result["EmptyTextTest"] == "Pass"
    assert result["fonts"] > 0
    assert result["numTxtObjects"] > 0
    assert result["Accessible"] is True


def test_empty_text_check_fails_for_pdf_without_selectable_text(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "empty_text_image_only_fail.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        check_empty_text(pdf, result)

    assert result["EmptyTextTest"] == "Fail"
    assert result["fonts"] == 0 or result["numTxtObjects"] == 0
    assert result["Accessible"] is True


# NOTE: this PDF lives in the "fixtures/protection" directory
def test_empty_text_check_still_passes_for_pdf_with_real_text_even_if_copying_is_blocked(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = (
        fixtures_dir / "protection" / "protection_encrypted_unselectable_fail.pdf"
    )
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        check_empty_text(pdf, result)

    assert result["EmptyTextTest"] == "Pass"
    assert result["fonts"] > 0
    assert result["numTxtObjects"] > 0
