import pikepdf


def init_analysis():
    res = {}
    res["numTxt"] = 0
    res["fontNames"] = set()
    return res


def merge_analyses(a, b):
    res = {}
    for key in a.keys():
        if key == "fontNames":
            res[key] = set.union(a[key], b[key])
        else:
            res[key] = a[key] + b[key]
    return res


def analyse_content(content, is_xobject: bool = False):
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
