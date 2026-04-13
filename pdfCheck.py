from datetime import datetime
import csv
import json
import os
import re
import xml.etree.ElementTree as ET

import dateparser
import pikepdf
import pytz
import typer
from bitstring import BitArray
from langcodes import Language, tag_parser
from pikepdf import Pdf, String
from pikepdf.models.metadata import decode_pdf_date

app = typer.Typer()

DEADLINE_DATE_STR = "2018-09-23T00:00:00+02:00"
OUTPUT_FIELDS = [
    "Site",
    "File",
    "Accessible",
    "TotallyInaccessible",
    "BrokenFile",
    "TaggedTest",
    "EmptyTextTest",
    "ProtectedTest",
    "TitleTest",
    "LanguageTest",
    "BookmarksTest",
    "Exempt",
    "Date",
    "hasTitle",
    "hasDisplayDocTitle",
    "hasLang",
    "InvalidLang",
    "Form",
    "xfa",
    "hasBookmarks",
    "hasXmp",
    "PDFVersion",
    "Creator",
    "Producer",
    "Pages",
    "_log",
    "fonts",
    "numTxtObjects",
]
debug = False


def extract_date(s: str) -> datetime:
    if s is None:
        return None
    if isinstance(s, String):
        s = str(s)
    try:
        return dateparser.parse(
            s,
            settings={"TIMEZONE": "UTC", "RETURN_AS_TIMEZONE_AWARE": True},
        )
    except ValueError:
        return None


def extract_pdf_date(s: str) -> datetime:
    if s is None:
        return None
    if isinstance(s, String):
        s = str(s)
    s = s.strip()
    if len(s) == 0:
        return None
    if s.startswith("CPY Document"):
        return None

    # manage malformed timezones (ex: +01, +1'0', +01'00', + 1' 0')
    match = re.search(r"\+([\d\':\s]+)$", s)
    if match is not None:
        tz = match.group(0)
        initial_tz = tz
        if len(tz) == 3:
            tz = tz + "00"
        if "'" in tz:
            normalized = re.search(r"\+\s?(\d+)\'\s?(\d+)\'?", tz)
            if normalized is not None:
                tz = "+%02d%02d" % (int(normalized.group(1)), int(normalized.group(2)))
            else:
                tz = "+0000"
        s = s.replace(initial_tz, tz)
    try:
        pdf_date = decode_pdf_date(s)
        # we add a timezone when it is missing
        # it can of course be inaccurate, but we don't really need a precision < 1 day
        if not (
            pdf_date.tzinfo is not None
            and pdf_date.tzinfo.utcoffset(pdf_date) is not None
        ):
            pdf_date = pdf_date.replace(tzinfo=pytz.utc)
        return pdf_date
    except ValueError:
        return extract_date(s)


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


def init_result(file_name: str, site: str = None):
    result = {}
    for field in OUTPUT_FIELDS:
        result[field] = None
    result["Site"] = site
    result["File"] = os.path.basename(file_name)
    result["_log"] = ""
    result["Accessible"] = True  # presumption of conformity :)
    result["Exempt"] = False
    result["TotallyInaccessible"] = False
    return result


def check_metadata_and_title(pdf, result):
    # check if is exempted? (based on which date?)
    meta = pdf.open_metadata()
    if meta is None:
        result["hasXmp"] = False
        result["Accessible"] = (
            False  # Matterhorn 06-001 # FIXME is it really an accessibility issue?
        )
        result["_log"] += "xmp "
        return

    result["hasXmp"] = True
    result["Creator"] = meta.get("xmp:CreatorTool")
    result["Producer"] = meta.get("pdf:Producer")

    xmp_modify_date = extract_date(meta.get("xmp:ModifyDate"))
    dc_modified_date = extract_date(meta.get("dc:Modified"))
    mod_date = extract_pdf_date(pdf.docinfo.get("/ModDate"))
    create_date = extract_date(meta.get("xmp:CreateDate"))
    creation_date = extract_pdf_date(pdf.docinfo.get("/CreationDate"))

    date = (
        xmp_modify_date or dc_modified_date or mod_date or create_date or creation_date
    )

    if date is not None:
        deadline_date = datetime.strptime(DEADLINE_DATE_STR, "%Y-%m-%dT%H:%M:%S%z")
        result["Date"] = str(date)
        if date < deadline_date:
            result["Exempt"] = True
    else:
        result["_log"] += "no date found, "

    # check if has Title
    result["TitleTest"] = "Pass"
    title = meta.get("dc:title") or pdf.docinfo.get(
        "/Title"
    )  # here we go further than Matterhorn 06-003 to avoid false positives
    viewer_prefs = pdf.Root.get("/ViewerPreferences")

    if title is None or len(str(title)) == 0:
        result["TitleTest"] = "Fail"
        result["hasTitle"] = False
        result["Accessible"] = False
        result["_log"] += "title, "
        return

    result["hasTitle"] = True

    if viewer_prefs is None:
        result["TitleTest"] = "Fail"
        result["hasDisplayDocTitle"] = False
        result["Accessible"] = False
        result["_log"] += "title, "
        return

    disp_doc_title = viewer_prefs.get("/DisplayDocTitle")
    if disp_doc_title is None:
        result["TitleTest"] = "Fail"  # Matterhorn 07-001
        result["hasDisplayDocTitle"] = False
        result["Accessible"] = False
        result["_log"] += "title, "
        return

    if disp_doc_title is False:  # Matterhorn 07-002
        result["TitleTest"] = "Fail"
        result["hasDisplayDocTitle"] = False
        result["Accessible"] = False
        result["_log"] += "title, "
    else:
        result["TitleTest"] = "Pass"
        result["hasDisplayDocTitle"] = True


def check_tagging(pdf, result):
    # check if Tagged
    # TODO: extend checks here by verifying that all objects in the document are tagged (cf Matterhorn Checkpoint 01)
    struct_tree_root = pdf.Root.get("/StructTreeRoot")
    if struct_tree_root is None:
        result["TaggedTest"] = "Fail"
        result["Accessible"] = False
        result["_log"] += "tagged, "
        return

    mark_info = pdf.Root.get("/MarkInfo")
    marked = mark_info.get("/Marked") if mark_info is not None else None

    if marked is None or marked is False:
        result["TaggedTest"] = "Fail"
        result["Accessible"] = False
        result["_log"] += "tagged, "
    else:
        result["TaggedTest"] = "Pass"


def check_protection(pdf, result):
    # check if not protected
    result["ProtectedTest"] = "Pass"
    if pdf.is_encrypted:  # Matterhorn 26-001
        if pdf.encryption.P is None:
            result["Accessible"] = False
            result["ProtectedTest"] = "Fail"

        if pdf.allow is None:
            result["_log"] += "permissions not found, should not happen"
        else:
            # according to the Matterhorn test 26-002 we should only test the 10th bit of P
            # but according to our tests, in Acrobat, the 5th bit and the R field are also used to give permissions to screen readers.
            # The algorithm behind pdf.allow.accessibility is here https://github.com/qpdf/qpdf/blob/8971443e4680fc1c0babe56da58cc9070a9dae2e/libqpdf/QPDF_encryption.cc#L1486
            # This algorithm works in most cases, except when the 10th bit is not set and the 5th bit is set. In this case Acrobat is considering that the 5th bit overrides the 10th bit and gives access.
            # I was able to test this only with a file where R=3. To be tested with R<3, but this case seems to be rare.
            bits = BitArray(intbe=pdf.encryption.P, length=16)
            bit10 = bits[16 - 10]
            bit5 = bits[16 - 5]
            # print(bits[16-3],bits[16-4],bits[16-5],bits[16-6],bits[16-9],bits[16-10],bits[16-11],bits[16-12])
            # print(pdf.allow)
            if (not bit10) and bit5:
                result["ProtectedTest"] = "Pass"
                result["_log"] += (
                    "P[10]="
                    + str(bit10)
                    + " P[5]="
                    + str(bit5)
                    + " R="
                    + str(pdf.encryption.R)
                    + ", "
                )
            else:
                result["ProtectedTest"] = "Pass" if pdf.allow.accessibility else "Fail"

            if result["ProtectedTest"] == "Fail":
                result["Accessible"] = False


def check_language(pdf, result):
    # check if has default language? is the default language valid?
    # "x-default" and "x-unknown" are not considered valid languages, as they are managed by screen readers as if no language was specified
    lang = pdf.Root.get("/Lang")
    if lang is None or len(str(lang)) == 0:
        result["LanguageTest"] = "Fail"
        result["hasLang"] = False
        result["Accessible"] = False
        result["_log"] += "lang, "
        return

    result["hasLang"] = True
    try:
        if not Language.get(str(lang)).is_valid():
            result["InvalidLang"] = True
            result["LanguageTest"] = "Fail"
            result["_log"] += "Default language is not valid: " + str(lang) + ", "
            result["Accessible"] = False
        else:
            result["LanguageTest"] = "Pass"
    except tag_parser.LanguageTagError:
        result["InvalidLang"] = True
        result["LanguageTest"] = "Fail"
        result["_log"] += "Default language is not valid: " + str(lang) + ", "
        result["Accessible"] = False


def check_forms(pdf, result):
    acro = pdf.Root.get("/AcroForm")
    if acro is None:
        return

    try:
        # warn users about Dynamic XFA
        # Dynamic XFA is not compliant with PDF/UA but seems that WCAG has nothing against it
        # cf https://technica11y.org/pdf-accessibility
        xfa = acro.get("/XFA")  # Matterhorn 25-001
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
                        if re.match(
                            r".*dynamicRender", d.tag
                        ):  # because of namespaces...
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


def check_bookmarks(pdf, result):
    outline = pdf.open_outline()
    result["hasBookmarks"] = True
    result["BookmarksTest"] = "Pass"
    if len(outline.root) == 0:
        result["hasBookmarks"] = False
        if len(pdf.pages) > 20:
            result["BookmarksTest"] = "Fail"
            result["Accessible"] = False
            result["_log"] += "no bookmarks and more than 20 pages, "
            # rule from Acrobat Pro accessibility checker
            # https://helpx.adobe.com/acrobat/using/create-verify-pdf-accessibility.html#Bookmarks


def check_empty_text(pdf, result):
    # try to detect if this PDF contains no text (ex: scanned document)
    # - if the document is not tagged and has no text, it will be inaccessible
    # - if the document is tagged and has no text, it can be accessible

    res = init_analysis()
    for page in pdf.pages:
        res = merge_analyses(res, analyse_content(page))

    result["fonts"] = len(res["fontNames"])
    if result["fonts"] != 0:
        result["_log"] += "fonts:" + ", ".join(res["fontNames"])
    result["numTxtObjects"] = res["numTxt"]

    result["EmptyTextTest"] = (
        "Fail" if (len(res["fontNames"]) == 0 or res["numTxt"] == 0) else "Pass"
    )


def finalize_result(result):
    if result["TaggedTest"] == "Fail" and result["EmptyTextTest"] == "Fail":
        result["TotallyInaccessible"] = True

    if result["ProtectedTest"] == "Fail":
        result["TotallyInaccessible"] = True


def check_file(file_name: str, site: str = None, debug: bool = False):
    result = init_result(file_name, site)

    try:
        pdf = Pdf.open(file_name)
        result["PDFVersion"] = pdf.pdf_version
        result["Pages"] = len(pdf.pages)

        check_metadata_and_title(pdf, result)
        check_tagging(pdf, result)
        check_protection(pdf, result)
        check_language(pdf, result)
        check_forms(pdf, result)
        check_bookmarks(pdf, result)
        check_empty_text(pdf, result)

    except pikepdf.qpdf.PdfError as err:
        result["BrokenFile"] = True
        result["Accessible"] = None
        result["_log"] += "PdfError: {0}".format(err)
    except pikepdf.qpdf.PasswordError as err:
        result["BrokenFile"] = True
        result["Accessible"] = None
        result["_log"] += "Password protected file: {0}".format(err)
    except ValueError as err:
        result["BrokenFile"] = True
        result["Accessible"] = None
        result["_log"] += "ValueError: {0}".format(err)

    finalize_result(result)
    return result


@app.command(name="tocsv")
def to_csv(
    site: str,
    inputfile: str,
    outputfile: str = "./out/pdfCheck.csv",
    debug: bool = False,
):
    # analyse file
    results = []
    result = check_file(inputfile, site, debug)
    out_fields = OUTPUT_FIELDS

    if not debug:
        del result["_log"]
        del result["fonts"]
        del result["numTxtObjects"]
        out_fields = OUTPUT_FIELDS[0 : len(OUTPUT_FIELDS) - 3]
    results.append(result)

    # export data as CSV
    csv_exists = os.path.exists(outputfile)
    with open(outputfile, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        if not csv_exists:
            writer.writeheader()
        writer.writerows(results)


@app.command(name="tojson")
def to_json(inputfile: str, debug: bool = False, pretty: bool = False):
    # analyse file
    result = check_file(inputfile)
    if not debug:
        del result["_log"]
        del result["fonts"]
        del result["numTxtObjects"]
    if pretty:
        print(json.dumps(result, indent=4))
    else:
        print(json.dumps(result))


if __name__ == "__main__":
    app()
