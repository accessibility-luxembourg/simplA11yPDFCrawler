from pathlib import Path

from pikepdf import Pdf

from scanner.checks import check_bookmarks


FIXTURE_SUBDIR = "bookmarks"


def open_pdf(path: Path) -> Pdf:
    return Pdf.open(str(path))


def test_bookmarks_check_passes_for_short_pdf_with_bookmarks(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "bookmarks_short_pass.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        check_bookmarks(pdf, result)

    assert result["hasBookmarks"] is True
    assert result["BookmarksTest"] == "Pass"
    assert result["Accessible"] is True


def test_bookmarks_check_passes_for_short_pdf_with_NO_bookmarks(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "no_bookmarks_short_pass.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        check_bookmarks(pdf, result)

    assert result["hasBookmarks"] is False
    assert result["BookmarksTest"] == "Pass"
    assert result["Accessible"] is True


def test_bookmarks_check_passes_for_long_pdf_with_bookmarks(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "bookmarks_long_pass.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        check_bookmarks(pdf, result)

    assert result["hasBookmarks"] is True
    assert result["BookmarksTest"] == "Pass"
    assert result["Accessible"] is True


def test_bookmarks_check_fails_for_long_pdf_with_NO_bookmarks(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "no_bookmarks_long_fail.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        check_bookmarks(pdf, result)

    assert result["hasBookmarks"] is False
    assert result["BookmarksTest"] == "Fail"
    assert result["Accessible"] is False
    assert "no bookmarks and more than 20 pages" in result["_log"]
