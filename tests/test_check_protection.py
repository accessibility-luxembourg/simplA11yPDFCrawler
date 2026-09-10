from pathlib import Path

from pikepdf import Pdf

from scanner.checks import check_protection
from scanner.scanner import check_file


FIXTURE_SUBDIR = "protection"


def open_pdf(path: Path) -> Pdf:
    return Pdf.open(str(path))


def test_protection_check_passes_for_unprotected_pdf(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "protection_pass.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        check_protection(pdf, result)

    assert result["ProtectedTest"] == "Pass"
    assert result["Accessible"] is True


def test_protection_check_passes_for_encrypted_pdf_when_accessibility_is_allowed(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "protection_encrypted_pass.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        check_protection(pdf, result)

    assert pdf.is_encrypted is True
    assert result["ProtectedTest"] == "Pass"
    assert result["Accessible"] is True


def test_check_file_marks_open_password_pdf_as_broken(
    fixtures_dir: Path,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "protection_encrypted_fail.pdf"
    result = check_file(str(pdf_path), site="example.com")

    assert result["BrokenFile"] is True
    assert result["Accessible"] is None
    assert "Password protected file" in result["_log"]


def test_protection_check_fails_for_openable_pdf_with_text_access_blocked(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = (
        fixtures_dir / FIXTURE_SUBDIR / "protection_encrypted_unselectable_fail.pdf"
    )
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        check_protection(pdf, result)

    assert result["ProtectedTest"] == "Fail"
    assert result["Accessible"] is False
