from scanner.report import build_json_report


def test_report_summary_says_no_problems_when_no_failed_rules():
    result = {
        "ProtectedTest": "Pass",
        "EmptyTextTest": "Pass",
        "TaggedTest": "Pass",
        "LanguageTest": "Pass",
        "TitleTest": "Pass",
        "BookmarksTest": "Pass",
        "TaggedAnnotationsTest": "NotApplicable",
        "FormFieldCount": 0,
        "TaggedFormFieldsTest": "NotApplicable",
        "FormsTest": "NotApplicable",
        "FiguresAltTextTest": "Pass",
        "NestedAltTextTest": "NotApplicable",
        "HidesAnnotationTest": "NotApplicable",
        "InvalidTRParents": "",
        "InvalidCellParents": "",
        "TablesWithoutHeaders": "",
        "IrregularTables": "",
        "InvalidListItemParents": "",
        "InvalidListChildren": "",
        "MalformedListNodes": "",
        "HeadingsTest": "Pass",
    }

    report = build_json_report(result, compatible=True)

    assert report["Summary"]["Failed"] == 0
    assert report["Summary"]["Description"] == (
        "The checker found no problems in this document."
    )


def test_report_maps_warn_to_failed_with_warning_severity_in_debug():
    result = {
        "ProtectedTest": "Pass",
        "EmptyTextTest": "Pass",
        "TaggedTest": "Pass",
        "LanguageTest": "Pass",
        "TitleTest": "Pass",
        "BookmarksTest": "Pass",
        "TaggedAnnotationsTest": "NotApplicable",
        "FormFieldCount": 0,
        "TaggedFormFieldsTest": "NotApplicable",
        "FormsTest": "NotApplicable",
        "FiguresAltTextTest": "Pass",
        "NestedAltTextTest": "NotApplicable",
        "HidesAnnotationTest": "Warn",
        "HidesAnnotationIssues": "(40, 0): Form has alt text and OBJR child",
        "InvalidTRParents": "",
        "InvalidCellParents": "",
        "TablesWithoutHeaders": "",
        "IrregularTables": "",
        "InvalidListItemParents": "",
        "InvalidListChildren": "",
        "MalformedListNodes": "",
        "HeadingsTest": "Pass",
    }

    report = build_json_report(result, debug=True)

    hides_annotation = next(
        rule
        for rule in report["Detailed Report"]["Alternate Text"]
        if rule["Rule"] == "Hides annotation"
    )

    assert hides_annotation["Status"] == "Failed"
    assert hides_annotation["Original status"] == "Warn"
    assert hides_annotation["Severity"] == "Warning"
