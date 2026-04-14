from __future__ import annotations

from typing import Any

import pikepdf

from scanner.models import StructureItem


def safe_name(obj: Any) -> str | None:
    """Return a readable string for pikepdf Names / Strings / other objects."""
    if obj is None:
        return None
    try:
        return str(obj)
    except Exception:
        return repr(obj)


def obj_get(obj: Any, key: str, default: Any = None) -> Any:
    """Safe dictionary-style access for pikepdf objects."""
    try:
        return obj.get(key, default)
    except Exception:
        return default


def as_kids(value: Any) -> list[Any]:
    """
    Normalize a PDF /K value into a list of child items without accidentally
    iterating through a single dictionary-like pikepdf object.

    /K may be:
    - None
    - a single structure element dictionary
    - an array of children
    - an integer MCID
    - a mixed object
    """
    if value is None:
        return []

    if isinstance(value, list):
        return value

    # If it already looks like a structure-ish object, keep it whole.
    try:
        if (
            obj_get(value, "/S") is not None
            or obj_get(value, "/K") is not None
            or obj_get(value, "/Type") is not None
        ):
            return [value]
    except Exception:
        pass

    # Otherwise, try treating it as an iterable array-like object.
    try:
        items = list(value)

        # If iteration produced scalar-ish values rather than child objects,
        # this likely was not a real child array.
        if items and all(not hasattr(item, "keys") for item in items):
            return [value]

        return items
    except Exception:
        return [value]


def extract_role_map(pdf: pikepdf.Pdf) -> dict[str, str]:
    """Read /RoleMap from /StructTreeRoot if present."""
    mapping: dict[str, str] = {}

    struct_tree_root = obj_get(pdf.Root, "/StructTreeRoot")
    if not struct_tree_root:
        return mapping

    role_map = obj_get(struct_tree_root, "/RoleMap")
    if not role_map:
        return mapping

    try:
        for key, value in role_map.items():
            k = safe_name(key)
            v = safe_name(value)
            if not k or not v:
                continue

            if k.startswith("/"):
                k = k[1:]
            if v.startswith("/"):
                v = v[1:]

            mapping[k] = v
    except Exception:
        pass

    return mapping


def normalize_struct_type(raw_type: Any, role_map: dict[str, str]) -> str | None:
    """
    Normalize a structure type like /Figure or /H1.
    Applies /RoleMap if available.
    """
    value = safe_name(raw_type)
    if not value:
        return None

    if value.startswith("/"):
        value = value[1:]

    return role_map.get(value, value)


def find_alt_text(struct_elem: Any) -> tuple[str | None, str | None]:
    """
    Try the most likely alt-text-related fields for a structure element.
    Return (text, source) where source is '/Alt' or '/ActualText'.
    """
    for key in ("/Alt", "/ActualText"):
        value = obj_get(struct_elem, key)
        if value is not None:
            text = safe_name(value)
            if text and text.strip():
                return text.strip(), key
    return None, None


def iter_structure_elements(node: Any) -> list[Any]:
    """
    Return child structure elements from /K for recursive traversal.

    For Phase 1 we:
    - ignore integer MCIDs
    - recurse only into dictionary-like children that look like structure nodes
    """
    kids = obj_get(node, "/K")
    if kids is None:
        return []

    results: list[Any] = []

    for item in as_kids(kids):
        try:
            if isinstance(item, int):
                continue
        except Exception:
            pass

        try:
            item_type = obj_get(item, "/S")
            item_kids = obj_get(item, "/K")
            if item_type is not None or item_kids is not None:
                results.append(item)
        except Exception:
            continue

    return results


def build_structure_item(
    node: Any,
    role_map: dict[str, str],
    depth: int,
) -> StructureItem | None:
    """Convert a raw structure node into a normalized StructureItem."""
    raw_type = safe_name(obj_get(node, "/S"))
    normalized_type = normalize_struct_type(obj_get(node, "/S"), role_map)

    if raw_type and raw_type.startswith("/"):
        raw_type = raw_type[1:]

    title = safe_name(obj_get(node, "/T"))
    alt_text, alt_source = find_alt_text(node)
    kids_count = len(as_kids(obj_get(node, "/K")))

    object_ref: str | None = None
    try:
        object_ref = repr(node.objgen)
    except Exception:
        object_ref = None

    if raw_type is None and normalized_type is None:
        return None

    return StructureItem(
        type=raw_type,
        normalized_type=normalized_type,
        depth=depth,
        title=title,
        alt=alt_text,
        kids_count=kids_count,
        object_ref=object_ref,
        alt_source=alt_source,
    )


def walk_structure_tree(
    node: Any,
    role_map: dict[str, str],
    depth: int = 0,
) -> list[StructureItem]:
    """
    Recursively walk structure elements and collect a flat list of normalized
    StructureItem objects.
    """
    results: list[StructureItem] = []

    item = build_structure_item(node, role_map, depth)
    if item is not None:
        results.append(item)

    for child in iter_structure_elements(node):
        results.extend(walk_structure_tree(child, role_map, depth + 1))

    return results


def load_structure_items(pdf: pikepdf.Pdf) -> list[StructureItem]:
    """
    Load normalized structure items from a tagged PDF.

    Returns a flat list in traversal order.
    If the PDF has no /StructTreeRoot, returns an empty list.
    """
    struct_tree_root = obj_get(pdf.Root, "/StructTreeRoot")
    if not struct_tree_root:
        return []

    role_map = extract_role_map(pdf)
    items: list[StructureItem] = []

    top_level = as_kids(obj_get(struct_tree_root, "/K"))
    for node in top_level:
        try:
            if isinstance(node, int):
                continue
        except Exception:
            pass

        items.extend(walk_structure_tree(node, role_map, depth=0))

    return items
