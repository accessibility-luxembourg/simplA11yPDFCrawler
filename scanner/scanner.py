import os

import pikepdf
from pikepdf import Pdf

from scanner.constants import OUTPUT_FIELDS
from scanner.checks import (
    check_bookmarks,
    check_empty_text,
    check_forms,
    check_language,
    check_metadata_and_title,
    check_protection,
    check_tagging,
)


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
