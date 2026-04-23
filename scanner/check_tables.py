from dataclasses import dataclass, field

from scanner.models import StructureItem


TABLE = "Table"
TABLE_ROW = "TR"
TABLE_HEADER_CELL = "TH"
TABLE_DATA_CELL = "TD"
TABLE_HEAD = "THead"
TABLE_BODY = "TBody"
TABLE_FOOT = "TFoot"
CAPTION = "Caption"

ALLOWED_TR_PARENTS = {TABLE, TABLE_HEAD, TABLE_BODY, TABLE_FOOT}
ALLOWED_CELL_PARENTS = {TABLE_ROW}
TABLE_CELL_TYPES = {TABLE_HEADER_CELL, TABLE_DATA_CELL}
TABLE_GROUP_TYPES = {TABLE_HEAD, TABLE_BODY, TABLE_FOOT}


@dataclass
class TableCell:
    item: StructureItem
    cell_type: str


@dataclass
class TableRow:
    item: StructureItem
    cells: list[TableCell] = field(default_factory=list)

    @property
    def cell_count(self) -> int:
        return len(self.cells)

    @property
    def has_header_cells(self) -> bool:
        return any(cell.cell_type == TABLE_HEADER_CELL for cell in self.cells)


@dataclass
class TableSection:
    item: StructureItem
    section_type: str
    rows: list[TableRow] = field(default_factory=list)


@dataclass
class TableModel:
    item: StructureItem
    sections: list[TableSection] = field(default_factory=list)
    direct_rows: list[TableRow] = field(default_factory=list)
    captions: list[StructureItem] = field(default_factory=list)

    @property
    def rows(self) -> list[TableRow]:
        rows: list[TableRow] = []
        rows.extend(self.direct_rows)
        for section in self.sections:
            rows.extend(section.rows)
        return rows

    @property
    def has_thead(self) -> bool:
        return any(section.section_type == TABLE_HEAD for section in self.sections)

    @property
    def has_tbody(self) -> bool:
        return any(section.section_type == TABLE_BODY for section in self.sections)

    @property
    def has_tfoot(self) -> bool:
        return any(section.section_type == TABLE_FOOT for section in self.sections)

    @property
    def all_cell_types(self) -> list[str]:
        types: list[str] = []
        for row in self.rows:
            for cell in row.cells:
                types.append(cell.cell_type)
        return types

    @property
    def has_headers(self) -> bool:
        return TABLE_HEADER_CELL in self.all_cell_types

    @property
    def row_cell_counts(self) -> list[int]:
        return [row.cell_count for row in self.rows]


def _direct_children(
    structure_items: list[StructureItem], start_index: int
) -> list[tuple[int, StructureItem]]:
    """
    Return the direct children of the node at start_index from the flat,
    depth-ordered structure list.
    """
    root = structure_items[start_index]
    children: list[tuple[int, StructureItem]] = []

    i = start_index + 1
    while i < len(structure_items):
        item = structure_items[i]

        if item.depth <= root.depth:
            break

        if item.depth == root.depth + 1:
            children.append((i, item))

        i += 1

    return children


def _row_from_index(structure_items: list[StructureItem], row_index: int) -> TableRow:
    """
    Build a TableRow from a TR structure item by collecting its direct TH/TD
    children.
    """
    row_item = structure_items[row_index]
    row = TableRow(item=row_item)

    for _, child in _direct_children(structure_items, row_index):
        if child.normalized_type in TABLE_CELL_TYPES:
            row.cells.append(TableCell(item=child, cell_type=child.normalized_type))

    return row


def _section_from_index(
    structure_items: list[StructureItem], section_index: int
) -> TableSection:
    """
    Build a TableSection (THead/TBody/TFoot) by collecting its direct TR
    children.
    """
    section_item = structure_items[section_index]
    section = TableSection(
        item=section_item,
        section_type=section_item.normalized_type,
    )

    for child_index, child in _direct_children(structure_items, section_index):
        if child.normalized_type == TABLE_ROW:
            section.rows.append(_row_from_index(structure_items, child_index))

    return section


def build_tables(structure_items: list[StructureItem]) -> list[TableModel]:
    """
    Convert flat structure items into table-specific models.

    This intentionally uses only generic StructureItem data.
    No table-specific fields are added to StructureItem itself.
    """
    tables: list[TableModel] = []

    for index, item in enumerate(structure_items):
        if item.normalized_type != TABLE:
            continue

        table = TableModel(item=item)

        for child_index, child in _direct_children(structure_items, index):
            if child.normalized_type == CAPTION:
                table.captions.append(child)
            elif child.normalized_type == TABLE_ROW:
                table.direct_rows.append(_row_from_index(structure_items, child_index))
            elif child.normalized_type in TABLE_GROUP_TYPES:
                table.sections.append(_section_from_index(structure_items, child_index))

        tables.append(table)

    return tables


def check_tables(structure_items: list[StructureItem], result: dict) -> None:
    """
    Inspect normalized structure items and report Adobe-aligned table findings.

    Current behavior:

    Fail:
    - TR whose parent is not Table, THead, TBody, or TFoot
    - TH/TD whose parent is not TR
    - any table with cells but no TH cells

    Warn:
    - table has THead but no TBody
    - table has TBody but no THead
    - empty THead / TBody / TFoot
    - empty TR
    - table has no rows
    - table has rows but no cells
    - uneven row lengths

    NotApplicable:
    - document is not tagged
    - no table-related structures are present

    Notes:
    - This version intentionally does not enforce Summary.
    - This version intentionally does not attempt span-aware regularity.
    - Caption placement/count can be added later.
    """
    result["TableCount"] = 0
    result["InvalidTRParents"] = ""
    result["InvalidCellParents"] = ""
    result["TablesWithoutHeaders"] = ""
    result["IrregularTables"] = ""

    if result.get("TaggedTest") != "Pass":
        result["TablesTest"] = "NotApplicable"
        return

    tables = build_tables(structure_items)
    rows = [item for item in structure_items if item.normalized_type == TABLE_ROW]
    cells = [
        item
        for item in structure_items
        if item.normalized_type in {TABLE_HEADER_CELL, TABLE_DATA_CELL}
    ]

    result["TableCount"] = len(tables)

    if not tables and not rows and not cells:
        result["TablesTest"] = "NotApplicable"
        return

    failures: list[str] = []
    warnings: list[str] = []
    header_failures: list[str] = []
    irregular_warnings: list[str] = []

    # Global structural failures: TR parentage
    for item in rows:
        ref = item.object_ref or "unknown-object"
        if item.parent_type not in ALLOWED_TR_PARENTS:
            failures.append(
                f"{ref}: TR parent is {item.parent_type or 'None'}, "
                f"expected Table, THead, TBody, or TFoot"
            )

    # Global structural failures: TH / TD parentage
    for item in cells:
        ref = item.object_ref or "unknown-object"
        if item.parent_type not in ALLOWED_CELL_PARENTS:
            failures.append(
                f"{ref}: {item.normalized_type} parent is {item.parent_type or 'None'}, "
                f"expected TR"
            )

    # Per-table checks
    for table in tables:
        table_ref = table.item.object_ref or "unknown-object"

        # Warn if only one of THead / TBody is present.
        # If both are absent, that is fine.
        if table.has_thead and not table.has_tbody:
            warnings.append(f"{table_ref}: Table has THead but no TBody")
        if table.has_tbody and not table.has_thead:
            warnings.append(f"{table_ref}: Table has TBody but no THead")

        # Warn for empty sections
        for section in table.sections:
            section_ref = section.item.object_ref or table_ref
            if not section.rows:
                warnings.append(f"{section_ref}: {section.section_type} is empty")

        # Warn for empty table / empty rows
        if not table.rows:
            warnings.append(f"{table_ref}: Table has no rows")
        else:
            for row in table.rows:
                row_ref = row.item.object_ref or table_ref
                if row.cell_count == 0:
                    warnings.append(f"{row_ref}: TR is empty")

        # Rows exist but no cells found anywhere
        if table.rows and not table.all_cell_types:
            warnings.append(f"{table_ref}: Table has rows but no cells")

        # Header failure: any cell-bearing table with no TH
        if table.all_cell_types and not table.has_headers:
            header_failures.append(f"{table_ref}: Table has no TH cells")
            if all(cell_type == TABLE_DATA_CELL for cell_type in table.all_cell_types):
                header_failures.append(f"{table_ref}: Table cells are all TD")

        # Regularity warning
        counts = [count for count in table.row_cell_counts if count > 0]
        if len(counts) >= 2 and len(set(counts)) > 1:
            irregular_warnings.append(
                f"{table_ref}: Uneven row lengths detected ({table.row_cell_counts})"
            )

    result["InvalidTRParents"] = " | ".join(
        msg for msg in failures if ": TR parent is " in msg
    )
    result["InvalidCellParents"] = " | ".join(
        msg for msg in failures if " expected TR" in msg
    )
    result["TablesWithoutHeaders"] = " | ".join(header_failures)
    result["IrregularTables"] = " | ".join(irregular_warnings)

    failures.extend(header_failures)
    warnings.extend(irregular_warnings)

    if failures:
        result["TablesTest"] = "Fail"
        result["Accessible"] = False
        result["_log"] += "tables-fail, "
    elif warnings:
        result["TablesTest"] = "Warn"
        result["_log"] += "tables-warn, "
    else:
        result["TablesTest"] = "Pass"
