from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from scanner.models import StructureItem
from scanner.structure import obj_get, safe_name


LINK_SUBTYPE = "/Link"
WIDGET_SUBTYPE = "/Widget"
LINK_STRUCT_TYPE = "Link"


@dataclass
class AnnotationInfo:
    object_ref: str | None
    page_number: int
    subtype_raw: str | None
    subtype: str | None
    flags: int | None
    rect: list[float] | None
    action_type: str | None = None
    destination: str | None = None
    is_widget: bool = False
    field_name: str | None = None


def _object_ref(obj: Any) -> str | None:
    try:
        return repr(obj.objgen)
    except Exception:
        return None


def _normalize_rect(value: Any) -> list[float] | None:
    if value is None:
        return None

    try:
        rect = [float(x) for x in value]
        if len(rect) == 4:
            return rect
    except Exception:
        pass

    return None


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except Exception:
        return None


def _field_name_from_widget(widget: Any) -> str | None:
    direct_name = safe_name(obj_get(widget, "/T"))
    if direct_name:
        return direct_name

    parent = obj_get(widget, "/Parent")
    if parent is not None:
        parent_name = safe_name(obj_get(parent, "/T"))
        if parent_name:
            return parent_name

    return None


def _destination_summary(annot: Any) -> tuple[str | None, str | None]:
    dest = obj_get(annot, "/Dest")
    if dest is not None:
        return "Dest", safe_name(dest)

    action = obj_get(annot, "/A")
    if action is None:
        return None, None

    action_type = safe_name(obj_get(action, "/S"))

    uri = obj_get(action, "/URI")
    if uri is not None:
        return action_type, safe_name(uri)

    action_dest = obj_get(action, "/D")
    if action_dest is not None:
        return action_type, safe_name(action_dest)

    return action_type, None


def iter_page_annotations(pdf) -> list[AnnotationInfo]:
    collected: list[AnnotationInfo] = []

    for page_index, page in enumerate(pdf.pages, start=1):
        annots = obj_get(page.obj, "/Annots")
        if annots is None:
            continue

        try:
            for annot in annots:
                subtype_raw = safe_name(obj_get(annot, "/Subtype"))
                subtype = (
                    subtype_raw[1:]
                    if subtype_raw and subtype_raw.startswith("/")
                    else subtype_raw
                )

                flags = _int_or_none(obj_get(annot, "/F"))
                rect = _normalize_rect(obj_get(annot, "/Rect"))
                action_type, destination = _destination_summary(annot)

                is_widget = subtype_raw == WIDGET_SUBTYPE
                field_name = _field_name_from_widget(annot) if is_widget else None

                collected.append(
                    AnnotationInfo(
                        object_ref=_object_ref(annot),
                        page_number=page_index,
                        subtype_raw=subtype_raw,
                        subtype=subtype,
                        flags=flags,
                        rect=rect,
                        action_type=action_type,
                        destination=destination,
                        is_widget=is_widget,
                        field_name=field_name,
                    )
                )
        except Exception:
            continue

    return collected


def check_annotations(
    pdf,
    structure_items: list[StructureItem],
    result: dict,
) -> None:
    result["AnnotationCount"] = 0
    result["AnnotationsFound"] = False
    result["AnnotationSubtypeCounts"] = ""
    result["LinkAnnotationCount"] = 0
    result["WidgetAnnotationCount"] = 0
    result["TaggedAnnotationsTest"] = "NotApplicable"
    result["AnnotationSummary"] = ""

    annotations = iter_page_annotations(pdf)

    result["AnnotationCount"] = len(annotations)
    result["AnnotationsFound"] = len(annotations) > 0

    if not annotations:
        return

    subtype_counts: dict[str, int] = {}
    summaries: list[str] = []

    for annot in annotations:
        subtype_key = annot.subtype or "Unknown"
        subtype_counts[subtype_key] = subtype_counts.get(subtype_key, 0) + 1

        if annot.subtype_raw == LINK_SUBTYPE:
            result["LinkAnnotationCount"] += 1

        if annot.is_widget:
            result["WidgetAnnotationCount"] += 1

        summaries.append(
            f"{annot.object_ref or 'unknown'}: "
            f"page={annot.page_number} "
            f"subtype={annot.subtype or 'Unknown'} "
            f"flags={annot.flags!r} "
            f"rect={annot.rect!r} "
            f"action={annot.action_type!r} "
            f"dest={annot.destination!r} "
            f"widget={annot.is_widget} "
            f"field={annot.field_name!r}"
        )

    result["AnnotationSubtypeCounts"] = " | ".join(
        f"{key}={value}" for key, value in sorted(subtype_counts.items())
    )
    result["AnnotationSummary"] = " | ".join(summaries)

    link_annotations = [a for a in annotations if a.subtype_raw == LINK_SUBTYPE]

    if not link_annotations:
        result["TaggedAnnotationsTest"] = "Warn"
        result["_log"] += "annotations-nolinks, "
        return

    if result.get("TaggedTest") != "Pass":
        result["TaggedAnnotationsTest"] = "Fail"
        result["Accessible"] = False
        result["_log"] += "annotations-untagged, "
        return

    link_structs = [
        item for item in structure_items if item.normalized_type == LINK_STRUCT_TYPE
    ]

    if not link_structs:
        result["TaggedAnnotationsTest"] = "Warn"
        result["_log"] += "annotations-tagging-warn, "
    else:
        result["TaggedAnnotationsTest"] = "Pass"
