from pathlib import Path

from pikepdf import Pdf

from scanner.check_tables import check_tables
from scanner.checks import check_tagging
from scanner.structure import load_structure_items


FIXTURE_SUBDIR = "tables"


def open_pdf(path: Path) -> Pdf:
    return Pdf.open(str(path))


def build_table_inputs(pdf: Pdf, result: dict):
    check_tagging(pdf, result)

    structure_items = []
    if pdf.Root.get("/StructTreeRoot") is not None:
        structure_items = load_structure_items(pdf)

    return structure_items


# Table 1 cell, TH: pass
def test_tables_check_passes_for_single_cell_table_with_th(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "tables_1cell_th_pass.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_table_inputs(pdf, result)
        check_tables(structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["TableCount"] >= 1
    assert result["TablesTest"] == "Pass"
    assert result["Accessible"] is True
    assert result["InvalidTRParents"] == ""
    assert result["InvalidCellParents"] == ""
    assert result["TablesWithoutHeaders"] == ""
    assert result["IrregularTables"] == ""


# Table 1 cell, TD: fail
def test_tables_check_fails_for_single_cell_table_with_td_only(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "tables_1cell_td_fail.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_table_inputs(pdf, result)
        check_tables(structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["TableCount"] >= 1
    assert result["TablesTest"] == "Fail"
    assert result["Accessible"] is False
    assert "Table has no TH cells" in result["TablesWithoutHeaders"]
    assert "Table cells are all TD" in result["TablesWithoutHeaders"]
    assert "tables-fail" in result["_log"]


# Table 2x2 with no THead or TBody: 1 row THs, 1 row TDs: pass
def test_tables_check_passes_for_2x2_table_without_sections_with_headers(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "tables_2x2_no_sections_pass.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_table_inputs(pdf, result)
        check_tables(structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["TableCount"] >= 1
    assert result["TablesTest"] == "Pass"
    assert result["Accessible"] is True
    assert result["InvalidTRParents"] == ""
    assert result["InvalidCellParents"] == ""
    assert result["TablesWithoutHeaders"] == ""
    assert result["IrregularTables"] == ""


# Table 2x2 with THead, TBody, 1 row THs, 1 row TDs: pass
def test_tables_check_passes_for_2x2_table_with_thead_and_tbody(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "tables_2x2_thead_tbody_pass.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_table_inputs(pdf, result)
        check_tables(structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["TableCount"] >= 1
    assert result["TablesTest"] == "Pass"
    assert result["Accessible"] is True
    assert result["InvalidTRParents"] == ""
    assert result["InvalidCellParents"] == ""
    assert result["TablesWithoutHeaders"] == ""
    assert result["IrregularTables"] == ""


# Table 2x2 with Caption, then THead, TBody, 1 row THs, 1 row TDs: pass
def test_tables_check_passes_for_2x2_table_with_caption_thead_tbody(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "tables_2x2_caption_thead_tbody_pass.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_table_inputs(pdf, result)
        check_tables(structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["TableCount"] >= 1
    assert result["TablesTest"] == "Pass"
    assert result["Accessible"] is True
    assert result["InvalidTRParents"] == ""
    assert result["InvalidCellParents"] == ""
    assert result["TablesWithoutHeaders"] == ""
    assert result["IrregularTables"] == ""


# Table 2x2 with no THead or TBody: both rows THs: pass
def test_tables_check_passes_for_2x2_table_with_all_th_cells(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "tables_2x2_all_th_pass.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_table_inputs(pdf, result)
        check_tables(structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["TableCount"] >= 1
    assert result["TablesTest"] == "Pass"
    assert result["Accessible"] is True
    assert result["TablesWithoutHeaders"] == ""
    assert result["IrregularTables"] == ""


# Table 2x2 with no THead or TBody: both rows TDs: fail
def test_tables_check_fails_for_2x2_table_with_all_td_cells(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "tables_2x2_all_td_fail.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_table_inputs(pdf, result)
        check_tables(structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["TableCount"] >= 1
    assert result["TablesTest"] == "Fail"
    assert result["Accessible"] is False
    assert "Table has no TH cells" in result["TablesWithoutHeaders"]
    assert "Table cells are all TD" in result["TablesWithoutHeaders"]
    assert "tables-fail" in result["_log"]


# Table 2x2, with THead but no TBody: warn
def test_tables_check_warns_for_table_with_thead_but_no_tbody(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "tables_thead_no_tbody_warn.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_table_inputs(pdf, result)
        check_tables(structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["TableCount"] >= 1
    assert result["TablesTest"] == "Warn"
    assert result["Accessible"] is True
    assert "tables-warn" in result["_log"]


# Table 2x2, with no THead but yes a TBody: warn
def test_tables_check_warns_for_table_with_tbody_but_no_thead(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "tables_tbody_no_thead_warn.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_table_inputs(pdf, result)
        check_tables(structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["TableCount"] >= 1
    assert result["TablesTest"] == "Warn"
    assert result["Accessible"] is True
    assert "tables-warn" in result["_log"]


# Table with empty THead and no TH anywhere: fail
def test_tables_check_fails_for_empty_thead_when_table_has_no_headers(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "tables_empty_thead_fail.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_table_inputs(pdf, result)
        check_tables(structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["TableCount"] >= 1
    assert result["TablesTest"] == "Fail"
    assert result["Accessible"] is False
    assert "Table has no TH cells" in result["TablesWithoutHeaders"]
    assert "tables-fail" in result["_log"]


# Table with empty TBody: warn
def test_tables_check_warns_for_empty_tbody(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "tables_empty_tbody_warn.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_table_inputs(pdf, result)
        check_tables(structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["TableCount"] >= 1
    assert result["TablesTest"] == "Warn"
    assert result["Accessible"] is True
    assert "tables-warn" in result["_log"]


# Table with empty TFoot: warn
def test_tables_check_warns_for_empty_tfoot(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "tables_empty_tfoot_warn.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_table_inputs(pdf, result)
        check_tables(structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["TableCount"] >= 1
    assert result["TablesTest"] == "Warn"
    assert result["Accessible"] is True
    assert "tables-warn" in result["_log"]


# Table with empty rows: warn
# TODO: test this with Adobe API
# From Adobe: To be accessible, tables must contain the same number of columns in each row, and rows in each column.
def test_tables_check_warns_for_empty_tr(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "tables_empty_tr_warn.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_table_inputs(pdf, result)
        check_tables(structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["TableCount"] >= 1
    assert result["TablesTest"] == "Warn"
    assert result["Accessible"] is True
    assert "tables-warn" in result["_log"]


# Table > TD: fail
def test_tables_check_fails_for_table_with_td_as_direct_child(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "tables_table_direct_td_fail.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_table_inputs(pdf, result)
        check_tables(structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["TablesTest"] == "Fail"
    assert result["Accessible"] is False
    assert "TD parent is Table, expected TR" in result["InvalidCellParents"]
    assert "tables-fail" in result["_log"]


# TR outside of a Table: fail
def test_tables_check_fails_for_tr_outside_table(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "tables_tr_outside_table_fail.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_table_inputs(pdf, result)
        check_tables(structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["TablesTest"] == "Fail"
    assert result["Accessible"] is False
    assert "expected Table, THead, TBody, or TFoot" in result["InvalidTRParents"]
    assert "tables-fail" in result["_log"]


# TD outside of a table: fail
def test_tables_check_fails_for_td_outside_table(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "tables_td_outside_table_fail.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_table_inputs(pdf, result)
        check_tables(structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["TablesTest"] == "Fail"
    assert result["Accessible"] is False
    assert "expected TR" in result["InvalidCellParents"]
    assert "tables-fail" in result["_log"]


# Table > TBody > TD: fail
def test_tables_check_fails_for_tbody_with_td_direct_child(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "tables_tbody_direct_td_fail.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_table_inputs(pdf, result)
        check_tables(structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["TablesTest"] == "Fail"
    assert result["Accessible"] is False
    assert "TD parent is TBody, expected TR" in result["InvalidCellParents"]
    assert "tables-fail" in result["_log"]


# Table > THead > TH: fail
def test_tables_check_fails_for_thead_with_th_direct_child(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "tables_thead_direct_th_fail.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_table_inputs(pdf, result)
        check_tables(structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["TablesTest"] == "Fail"
    assert result["Accessible"] is False
    assert "TH parent is THead, expected TR" in result["InvalidCellParents"]
    assert "tables-fail" in result["_log"]


# Table > TFoot > TD: fail
def test_tables_check_fails_for_tfoot_with_td_direct_child(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "tables_tfoot_direct_td_fail.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_table_inputs(pdf, result)
        check_tables(structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["TablesTest"] == "Fail"
    assert result["Accessible"] is False
    assert "TD parent is TFoot, expected TR" in result["InvalidCellParents"]
    assert "tables-fail" in result["_log"]


# Table with no rows at all: fail
def test_tables_check_fails_for_empty_table(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "tables_empty_table_fail.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_table_inputs(pdf, result)
        check_tables(structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["TableCount"] >= 1
    assert result["TablesTest"] == "Fail"
    assert result["Accessible"] is False
    assert "Table has no TH cells" in result["TablesWithoutHeaders"]
    assert "tables-fail" in result["_log"]


def test_tables_check_is_not_applicable_for_tagged_pdf_with_no_tables(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "tables_none_na.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_table_inputs(pdf, result)
        check_tables(structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["TableCount"] == 0
    assert result["InvalidTRParents"] == ""
    assert result["InvalidCellParents"] == ""
    assert result["TablesWithoutHeaders"] == ""
    assert result["IrregularTables"] == ""
    assert result["TablesTest"] == "NotApplicable"
    assert result["Accessible"] is True


def test_tables_check_is_not_applicable_for_untagged_pdf(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "tables_untagged_na.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_table_inputs(pdf, result)
        check_tables(structure_items, result)

    assert result["TaggedTest"] == "Fail"
    assert result["TableCount"] == 0
    assert result["InvalidTRParents"] == ""
    assert result["InvalidCellParents"] == ""
    assert result["TablesWithoutHeaders"] == ""
    assert result["IrregularTables"] == ""
    assert result["TablesTest"] == "NotApplicable"
