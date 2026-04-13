import pikepdf


def init_analysis():
    """Create a fresh, empty analysis result dictionary.

    Returns:
        A dict with keys ``numTxt`` (int, 0) and ``fontNames`` (empty set),
        ready to be populated by :func:`analyse_content` or combined via
        :func:`merge_analyses`.
    """
    res = {}
    res["numTxt"] = 0
    res["fontNames"] = set()
    return res


def merge_analyses(a, b):
    """Combine two analysis result dicts into one.

    Font name sets are merged via union; all other numeric fields (e.g.
    ``numTxt``) are summed.

    Args:
        a: An analysis dict as returned by :func:`init_analysis` or
           :func:`analyse_content`.
        b: A second analysis dict with the same keys.

    Returns:
        A new analysis dict whose ``fontNames`` is the union of both sets and
        whose remaining fields are the element-wise sums.
    """
    res = {}
    for key in a.keys():
        if key == "fontNames":
            res[key] = set.union(a[key], b[key])
        else:
            res[key] = a[key] + b[key]
    return res


def analyse_content(content, is_xobject: bool = False):
    """Analyse a PDF page or Form XObject for font usage and text objects.

    Traverses the resource dictionary of ``content`` to collect all font
    names (from ``/FontDescriptor/FontName`` or ``/BaseFont``) and count
    ``Tf`` (text-font select) operators in the content stream. Recursively
    processes embedded Form XObjects (excluding reference XObjects).

    Args:
        content: A pikepdf page or Form XObject with a ``/Resources``
                 dictionary.
        is_xobject: ``True`` when ``content`` is a Form XObject rather than a
                    top-level page. Currently used as a marker but does not
                    change processing logic.

    Returns:
        An analysis dict (see :func:`init_analysis`) populated with:
        - ``fontNames``: set of font name strings found in the resource dict.
        - ``numTxt``: count of ``Tf`` operators encountered in content streams.
    """
    res = init_analysis()
    if content.get("/Resources") is not None:
        xobject = content.Resources.get("/XObject")
        if xobject is not None:
            for key in xobject:
                if (
                    str(xobject[key].get("/Subtype")) == "/Form"
                    and xobject[key].get("/Ref") is None
                ):
                    res = merge_analyses(res, analyse_content(xobject[key], True))

        if content.Resources.get("/Font") is not None:
            # get all font names
            for key in content.Resources.Font:
                font = content.Resources.Font[key]
                font_name = None
                if font.get("/FontDescriptor") is not None:
                    font_name = str(content.Resources.Font[key].FontDescriptor.FontName)
                else:
                    font_name = str(content.Resources.Font[key].get("/BaseFont"))
                res["fontNames"].add(font_name)

            # count the number of text objects
            for operands, operator in pikepdf.parse_content_stream(content, "Tf"):
                res["numTxt"] += 1

    return res
