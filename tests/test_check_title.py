from pathlib import Path

from pikepdf import Pdf

from scanner.checks import check_metadata_and_title


def open_pdf(path: Path) -> Pdf:
    return Pdf.open(str(path))


def test_title_check_passes_when_title_and_display_doc_title_are_present(
    title_fixtures_dir: Path,
    make_result,
):
    pdf_path = title_fixtures_dir / "title_pass.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        check_metadata_and_title(pdf, result)

    assert result["hasXmp"] is True
    assert result["hasTitle"] is True
    assert result["hasDisplayDocTitle"] is True
    assert result["TitleTest"] == "Pass"


def test_title_check_fails_when_title_is_missing(
    title_fixtures_dir: Path,
    make_result,
):
    pdf_path = title_fixtures_dir / "title_fail.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        check_metadata_and_title(pdf, result)

    assert result["TitleTest"] == "Fail"
    assert result["hasTitle"] is False
    assert result["Accessible"] is False
    assert "title" in result["_log"]


def test_title_check_fails_when_display_doc_title_flag_is_missing_or_false(
    title_fixtures_dir: Path,
    make_result,
):
    pdf_path = title_fixtures_dir / "title_display_flag_false.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        check_metadata_and_title(pdf, result)

    assert result["TitleTest"] == "Fail"
    assert result["hasTitle"] is True
    assert result["hasDisplayDocTitle"] is False
    assert result["Accessible"] is False
    assert "title" in result["_log"]
