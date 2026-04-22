from scanner.models import StructureItem


LIST_CONTAINER = "L"
LIST_ITEM = "LI"
LIST_LABEL = "Lbl"
LIST_BODY = "LBody"
LIST_CAPTION = "Caption"
DIV = "Div"

ALLOWED_L_CHILDREN = {LIST_ITEM, LIST_CAPTION, LIST_CONTAINER, DIV}

# These are not all guaranteed “perfect” PDF-spec combinations.
# They are the child types we currently allow without warning based on
# Adobe behavior you tested plus common tagged-PDF patterns.
ALLOWED_LI_CHILDREN_WITHOUT_WARNING = {
    LIST_LABEL,
    LIST_BODY,
    LIST_CONTAINER,  # hierarchical nested list directly inside LI
    DIV,
}

# Direct content children inside LI are not ideal, but Adobe does not flag them.
# We warn instead of fail.
DIRECT_CONTENT_CHILDREN_THAT_WARN = {
    "P",
    "Span",
}


def check_lists(structure_items: list[StructureItem], result: dict) -> None:
    """
    Inspect normalized structure items and report Adobe-aligned list findings.

    Current behavior:

    Fail:
    - LI whose parent is not L
    - L with disallowed immediate child types

    Warn:
    - LI missing LBody
    - empty LI
    - LBody exists but is empty
    - LI has unusual direct children
    - L is empty

    Do nothing:
    - missing Lbl
    - LI with only Lbl
    - nested L inside LBody
    - nested L inside LI
    - nested L inside L
    - nested L inside Div
    - Caption first/last under L

    NotApplicable:
    - document is not tagged
    - no list structures are present
    """
    result["ListCount"] = 0
    result["InvalidListItemParents"] = ""
    result["InvalidListChildren"] = ""
    result["MalformedListNodes"] = ""

    if result.get("TaggedTest") != "Pass":
        result["ListsTest"] = "NotApplicable"
        return

    lists = [item for item in structure_items if item.normalized_type == LIST_CONTAINER]
    list_items = [item for item in structure_items if item.normalized_type == LIST_ITEM]
    lbodies = [item for item in structure_items if item.normalized_type == LIST_BODY]

    result["ListCount"] = len(lists)

    if not lists and not list_items:
        result["ListsTest"] = "NotApplicable"
        return

    failures: list[str] = []
    warnings: list[str] = []
    invalid_children: list[str] = []

    # Fail or warn on L containers
    for item in lists:
        ref = item.object_ref or "unknown-object"
        child_types = item.child_types

        if not child_types:
            warnings.append(f"{ref}: L is empty")
            continue

        disallowed_children = [
            child_type
            for child_type in child_types
            if child_type not in ALLOWED_L_CHILDREN
        ]
        if disallowed_children:
            failures.append(
                f"{ref}: L has disallowed children {', '.join(disallowed_children)}"
            )

    # Fail or warn on LI items
    for item in list_items:
        ref = item.object_ref or "unknown-object"
        child_types = item.child_types
        child_type_set = set(child_types)

        if item.parent_type != LIST_CONTAINER:
            failures.append(
                f"{ref}: LI parent is {item.parent_type or 'None'}, expected L"
            )

        if not child_types:
            warnings.append(f"{ref}: LI is empty")
            continue

        if LIST_BODY not in child_type_set:
            warnings.append(f"{ref}: LI missing LBody")

        unusual_children = []
        for child_type in child_types:
            if child_type in ALLOWED_LI_CHILDREN_WITHOUT_WARNING:
                continue
            if child_type in DIRECT_CONTENT_CHILDREN_THAT_WARN:
                unusual_children.append(child_type)
                continue

            # Anything else under LI is unusual enough to warn about for now.
            unusual_children.append(child_type)

        if unusual_children:
            invalid_children.append(
                f"{ref}: LI has unusual children {', '.join(unusual_children)}"
            )

    # Fail or warn on LBody nodes
    for item in lbodies:
        ref = item.object_ref or "unknown-object"

        if item.parent_type != LIST_ITEM:
            failures.append(
                f"{ref}: LBody parent is {item.parent_type or 'None'}, expected LI"
            )

        if not item.child_types:
            warnings.append(f"{ref}: LBody is empty")

    result["InvalidListItemParents"] = " | ".join(
        msg for msg in failures if "LI parent is" in msg
    )
    result["InvalidListChildren"] = " | ".join(invalid_children)
    result["MalformedListNodes"] = " | ".join(
        [msg for msg in warnings if "missing LBody" in msg or "is empty" in msg]
        + [
            msg
            for msg in failures
            if "L has disallowed children" in msg or "LBody parent is" in msg
        ]
    )

    if failures:
        result["ListsTest"] = "Fail"
        result["Accessible"] = False
        result["_log"] += "lists-fail, "
    elif warnings or invalid_children:
        result["ListsTest"] = "Warn"
        result["_log"] += "lists-warn, "
    else:
        result["ListsTest"] = "Pass"
