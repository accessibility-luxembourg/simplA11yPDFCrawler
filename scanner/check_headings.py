from scanner.models import StructureItem


HEADING_TYPES = {"H", "H1", "H2", "H3", "H4", "H5", "H6"}


def heading_level(tag_name: str) -> int | None:
    """
    Return heading level for H1-H6.
    Treat plain H as unknown.
    """
    if tag_name == "H":
        return None

    if len(tag_name) == 2 and tag_name.startswith("H") and tag_name[1].isdigit():
        level = int(tag_name[1])
        if 1 <= level <= 6:
            return level

    return None


def check_headings(structure_items: list[StructureItem], result: dict) -> None:
    """
    Inspect normalized structure items and report basic heading hierarchy findings.

    Tagged PDF rules:
    - Pass: headings are present and no obvious hierarchy issues are found
    - Warn: plain H tags are present, first known heading is not H1,
            or no headings are found in an otherwise tagged document
    - Fail: at least one obvious skipped level is found (e.g. H1 -> H3)

    Untagged PDF fallback:
    - NotApplicable: heading analysis depends on structure tagging
    """
    result["HeadingCount"] = 0
    result["HeadingSequence"] = ""
    result["HeadingIssues"] = ""

    if result.get("TaggedTest") != "Pass":
        result["HeadingsTest"] = "NotApplicable"
        return

    headings = [
        item for item in structure_items if item.normalized_type in HEADING_TYPES
    ]

    result["HeadingCount"] = len(headings)

    if not headings:
        result["HeadingsTest"] = "Warn"
        result["HeadingIssues"] = "No headings found in tagged document"
        result["_log"] += "headings-none, "
        return

    sequence = [item.normalized_type for item in headings]
    result["HeadingSequence"] = " > ".join(sequence)

    issues: list[str] = []
    previous_known_level: int | None = None
    first_known_level: int | None = None
    plain_h_found = False

    for heading in headings:
        tag = heading.normalized_type
        level = heading_level(tag)

        if tag == "H":
            plain_h_found = True

        if level is None:
            continue

        if first_known_level is None:
            first_known_level = level

        if previous_known_level is not None and level > previous_known_level + 1:
            issues.append(f"Skipped heading level: H{previous_known_level} -> H{level}")

        previous_known_level = level

    if plain_h_found:
        issues.append("Plain H tag encountered")

    if first_known_level is not None and first_known_level != 1:
        issues.append(f"First known heading is H{first_known_level}, not H1")

    result["HeadingIssues"] = " | ".join(issues)

    skipped_level_issues = [
        issue for issue in issues if issue.startswith("Skipped heading level:")
    ]

    if skipped_level_issues:
        result["HeadingsTest"] = "Fail"
        result["Accessible"] = False
        result["_log"] += "headings-skip, "
    elif issues:
        result["HeadingsTest"] = "Warn"
        result["_log"] += "headings-warn, "
    else:
        result["HeadingsTest"] = "Pass"
