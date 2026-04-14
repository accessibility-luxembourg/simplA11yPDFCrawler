from scanner.models import StructureItem


def check_figures(
    structure_items: list[StructureItem],
    result: dict,
    image_info: dict[str, int] | None = None,
) -> None:
    """
    Inspect normalized structure items and report basic figure/alt-text findings.

    Tagged PDF rules:
    - Pass: every Figure has /Alt
    - Warn: no missing alt, but at least one Figure relies only on /ActualText
    - Fail: at least one Figure has neither /Alt nor /ActualText

    Untagged PDF fallback:
    - Fail: image objects are present, but no figure tagging is available
    - NotApplicable: no image objects detected
    """
    if image_info is None:
        image_info = {"ImageObjectsFound": 0, "PagesWithImages": 0}

    result["ImageObjectsFound"] = image_info["ImageObjectsFound"]
    result["PagesWithImages"] = image_info["PagesWithImages"]

    result["FiguresFound"] = 0
    result["FiguresWithAlt"] = 0
    result["FiguresWithActualTextOnly"] = 0
    result["FiguresWithoutAlt"] = 0

    # Untagged fallback:
    # if the PDF is not tagged, structure-based figure analysis is not reliable.
    if result.get("TaggedTest") != "Pass":
        if image_info["ImageObjectsFound"] > 0:
            result["FiguresAltTextTest"] = "Fail"
            result["Accessible"] = False
            result["_log"] += "untagged-images, "
        else:
            result["FiguresAltTextTest"] = "NotApplicable"
        return

    figures = [item for item in structure_items if item.normalized_type == "Figure"]

    result["FiguresFound"] = len(figures)

    if not figures:
        result["FiguresAltTextTest"] = "Pass"
        return

    for fig in figures:
        if not fig.alt:
            result["FiguresWithoutAlt"] += 1
        elif fig.alt_source == "/Alt":
            result["FiguresWithAlt"] += 1
        elif fig.alt_source == "/ActualText":
            result["FiguresWithActualTextOnly"] += 1
        else:
            result["FiguresWithAlt"] += 1

    if result["FiguresWithoutAlt"] > 0:
        result["FiguresAltTextTest"] = "Fail"
        result["Accessible"] = False
        result["_log"] += "figures-alt, "
    elif result["FiguresWithActualTextOnly"] > 0:
        result["FiguresAltTextTest"] = "Warn"
        result["_log"] += "figures-actualtext, "
    else:
        result["FiguresAltTextTest"] = "Pass"
