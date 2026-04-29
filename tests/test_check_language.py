from pathlib import Path

from pikepdf import Pdf

from scanner.checks.document import check_language


FIXTURE_SUBDIR = "language"


def open_pdf(path: Path) -> Pdf:
    return Pdf.open(str(path))


def test_language_check_passes_for_valid_language(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "language_pass.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        check_language(pdf, result)

    assert result["LanguageTest"] == "Pass"
    assert result["hasLang"] is True
    assert result["Accessible"] is True


def test_language_check_fails_when_language_is_missing(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "language_fail.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        check_language(pdf, result)

    assert result["LanguageTest"] == "Fail"
    assert result["hasLang"] is False
    assert result["Accessible"] is False
    assert "lang" in result["_log"]


def test_language_check_fails_when_language_is_invalid(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "language_invalid.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        check_language(pdf, result)

    assert result["LanguageTest"] == "Fail"
    assert result["hasLang"] is True
    assert result["InvalidLang"] is True
    assert result["Accessible"] is False
    assert "Default language is not valid" in result["_log"]
