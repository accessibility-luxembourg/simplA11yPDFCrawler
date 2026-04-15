from pathlib import Path

from pikepdf import Pdf

from scanner.checks import check_tagging


def open_pdf(path: Path) -> Pdf:
    return Pdf.open(str(path))


def test_tagging_check_passes_for_tagged_pdf(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / "tagging" / "tagging_pass.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        check_tagging(pdf, result)

    assert result["TaggedTest"] == "Pass"
    assert result["Accessible"] is True
    assert "tagged" not in result["_log"]


def test_tagging_check_fails_for_untagged_pdf(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / "tagging" / "tagging_fail.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        check_tagging(pdf, result)

    assert result["TaggedTest"] == "Fail"
    assert result["Accessible"] is False
    assert "tagged" in result["_log"]
