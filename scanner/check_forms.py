from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any

from scanner.models import StructureItem
from scanner.structure import obj_get, safe_name


FORM_STRUCT_TYPE = "Form"
WIDGET_SUBTYPE = "/Widget"

FIELD_TYPE_MAP = {
    "/Btn": "button",
    "/Tx": "text",
    "/Ch": "choice",
    "/Sig": "signature",
}


@dataclass
class FormFieldInfo:
    object_ref: str | None
    field_type_raw: str | None
    field_type: str | None
    field_name: str | None
    description: str | None
    description_source: str | None
    widget_count: int = 0
    page_refs: list[str] = field(default_factory=list)


def _object_ref(obj: Any) -> str | None:
    try:
        return repr(obj.objgen)
    except Exception:
        return None


def _normalize_field_type(value: Any) -> str | None:
    raw = safe_name(value)
    if raw is None:
        return None
    return FIELD_TYPE_MAP.get(raw, raw)


def _non_empty_text(value: Any) -> str | None:
    text = safe_name(value)
    if text is None:
        return None
    text = text.strip()
    return text or None


def _field_description(field: Any) -> tuple[str | None, str | None]:
    """
    Return the best available accessibility description text and its source.

    Adobe's accessibility checker does not consider "field-name" (/T) as a valid a user-facing description.
    """
    for key, source in (
        ("/TU", "tooltip"),
        ("/TM", "mapping-name"),
        # ("/T", "field-name"),
    ):
        value = _non_empty_text(obj_get(field, key))
        if value:
            return value, source

    return None, None


def _collect_widget_annotations(field: Any) -> list[Any]:
    widgets: list[Any] = []

    subtype = safe_name(obj_get(field, "/Subtype"))
    if subtype == WIDGET_SUBTYPE:
        widgets.append(field)

    kids = obj_get(field, "/Kids")
    if kids is not None:
        try:
            for kid in kids:
                kid_subtype = safe_name(obj_get(kid, "/Subtype"))
                if kid_subtype == WIDGET_SUBTYPE:
                    widgets.append(kid)
        except Exception:
            pass

    return widgets


def _page_ref_from_widget(widget: Any) -> str | None:
    page = obj_get(widget, "/P")
    if page is None:
        return None
    return _object_ref(page)


def iter_form_fields(pdf) -> list[FormFieldInfo]:
    acro = pdf.Root.get("/AcroForm")
    if acro is None:
        return []

    try:
        fields = acro.get("/Fields")
    except Exception:
        return []

    if not fields:
        return []

    collected: list[FormFieldInfo] = []

    try:
        for field in fields:
            field_type_raw = safe_name(obj_get(field, "/FT"))
            field_type = _normalize_field_type(obj_get(field, "/FT"))
            field_name = _non_empty_text(obj_get(field, "/T"))
            description, description_source = _field_description(field)

            widgets = _collect_widget_annotations(field)
            page_refs: list[str] = []

            for widget in widgets:
                page_ref = _page_ref_from_widget(widget)
                if page_ref and page_ref not in page_refs:
                    page_refs.append(page_ref)

            collected.append(
                FormFieldInfo(
                    object_ref=_object_ref(field),
                    field_type_raw=field_type_raw,
                    field_type=field_type,
                    field_name=field_name,
                    description=description,
                    description_source=description_source,
                    widget_count=len(widgets),
                    page_refs=page_refs,
                )
            )
    except Exception:
        return collected

    return collected


def check_forms(pdf, result: dict) -> None:
    """
    Legacy form detection:
    - detect AcroForm
    - detect dynamic XFA
    - set Form
    - clear Exempt when fields exist
    """
    acro = pdf.Root.get("/AcroForm")
    if acro is None:
        return

    try:
        xfa = acro.get("/XFA")
        config_pos = -1
        found = False
        if xfa is not None:
            try:
                for n in range(0, len(xfa) - 1):
                    if xfa[n] == "config":
                        config_pos = n + 1
                        found = True
                        break
                if found and xfa[config_pos] is not None:
                    xml_str = xfa[config_pos].read_bytes().decode()
                    document = ET.fromstring(xml_str)
                    for d in document.iter():
                        if re.match(r".*dynamicRender", d.tag):
                            if d.text == "required":
                                result["xfa"] = True
                                result["_log"] += "xfa, "
            except TypeError:
                result["_log"] += "malformed xfa, "
    except ValueError:
        result["_log"] += "malformed xfa, "

    try:
        fields = acro.get("/Fields")
        if fields is not None and len(fields) != 0:
            result["Form"] = True
            result["Exempt"] = False
    except ValueError:
        result["_log"] += "malformed Form fields, "


def check_form_fields(
    pdf,
    structure_items: list[StructureItem],
    result: dict,
) -> None:
    result["FormFieldCount"] = 0
    result["FieldsWithoutDescription"] = ""
    result["TaggedFormFieldsTest"] = "NotApplicable"
    result["UnclearFieldAssociations"] = ""

    fields = iter_form_fields(pdf)
    result["FormFieldCount"] = len(fields)

    if not fields:
        result["FormsTest"] = "NotApplicable"
        result["TaggedFormFieldsTest"] = "NotApplicable"
        return

    missing_descriptions: list[str] = []
    unclear_associations: list[str] = []
    summaries: list[str] = []

    for field in fields:
        ref = field.object_ref or field.field_name or "unknown-field"

        if not field.description:
            missing_descriptions.append(f"{ref}: missing description")

        if field.widget_count == 0:
            unclear_associations.append(f"{ref}: no widget annotation found")
        elif not field.page_refs:
            unclear_associations.append(
                f"{ref}: widget annotation has no page association"
            )

        summaries.append(
            f"{ref}: "
            f"type={field.field_type or 'unknown'} "
            f"name={field.field_name!r} "
            f"desc={field.description!r} "
            f"desc_source={field.description_source or 'none'} "
            f"widgets={field.widget_count} "
            f"pages={field.page_refs}"
        )

    result["FieldsWithoutDescription"] = " | ".join(missing_descriptions)
    result["UnclearFieldAssociations"] = " | ".join(unclear_associations)
    result["FormFieldSummary"] = " | ".join(summaries)

    if missing_descriptions:
        result["FormsTest"] = "Fail"
        result["Accessible"] = False
        result["_log"] += "forms-fail, "
    else:
        result["FormsTest"] = "Pass"

    if result.get("TaggedTest") != "Pass":
        result["TaggedFormFieldsTest"] = "Fail"
        result["Accessible"] = False
        result["_log"] += "forms-untagged, "
        return

    form_structs = [
        item for item in structure_items if item.normalized_type == FORM_STRUCT_TYPE
    ]

    if not form_structs or unclear_associations:
        result["TaggedFormFieldsTest"] = "Warn"
        result["_log"] += "forms-tagging-warn, "
    else:
        result["TaggedFormFieldsTest"] = "Pass"
