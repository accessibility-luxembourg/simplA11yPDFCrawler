import re
import xml.etree.ElementTree as ET

from datetime import datetime
from bitstring import BitArray
from langcodes import Language, tag_parser

from scanner.constants import DEADLINE_DATE_STR
from scanner.dates import extract_date, extract_pdf_date
from scanner.text_analysis import analyse_content, init_analysis, merge_analyses


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
