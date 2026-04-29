from pathlib import Path

from pikepdf import Pdf

from scanner.check_annotations import check_annotations
from scanner.checks import check_tagging
from scanner.structure import load_structure_items


FIXTURE_SUBDIR = "annotations"


def open_pdf(path: Path) -> Pdf:
    return Pdf.open(str(path))


def build_annotation_inputs(pdf: Pdf, result: dict):
    check_tagging(pdf, result)

    structure_items = []
    if pdf.Root.get("/StructTreeRoot") is not None:
        structure_items = load_structure_items(pdf)

    return structure_items


# Tagged PDF with no annotations at all: annotation checks are not applicable
def test_check_annotations_is_not_applicable_when_no_annotations(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "annotations_none_na.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_annotation_inputs(pdf, result)
        check_annotations(pdf, structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["AnnotationCount"] == 0
    assert result["AnnotationsFound"] is False
    assert result["LinkAnnotationCount"] == 0
    assert result["WidgetAnnotationCount"] == 0
    assert result["AnnotationSubtypeCounts"] == ""
    assert result["AnnotationSummary"] == ""
    assert result["TaggedAnnotationsTest"] == "NotApplicable"
    assert result["Accessible"] is True


# Untagged PDF with a link annotation: fail tagged annotations check
def test_check_annotations_fails_for_untagged_pdf_with_link_annotation(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "annotations_untagged_link_fail.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_annotation_inputs(pdf, result)
        check_annotations(pdf, structure_items, result)

    assert result["TaggedTest"] == "Fail"
    assert result["AnnotationCount"] >= 1
    assert result["AnnotationsFound"] is True
    assert result["LinkAnnotationCount"] >= 1
    assert result["TaggedAnnotationsTest"] == "Fail"
    assert result["Accessible"] is False
    assert "annotations-untagged" in result["_log"]


# Tagged PDF with a link annotation but no Link structure elements: warn
def test_check_annotations_warns_for_tagged_pdf_with_link_annotation_but_no_link_structure(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = (
        fixtures_dir / FIXTURE_SUBDIR / "annotations_tagged_link_no_struct_warn.pdf"
    )

    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_annotation_inputs(pdf, result)
        check_annotations(pdf, structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["AnnotationCount"] >= 1
    assert result["AnnotationsFound"] is True
    assert result["LinkAnnotationCount"] >= 1
    assert result["TaggedAnnotationsTest"] == "Warn"
    assert result["Accessible"] is True
    assert "annotations-tagging-warn" in result["_log"]


# Tagged PDF with a link annotation and Link structure elements: pass
def test_check_annotations_passes_for_tagged_pdf_with_link_annotation_and_link_structure(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = (
        fixtures_dir / FIXTURE_SUBDIR / "annotations_tagged_link_with_struct_pass.pdf"
    )
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_annotation_inputs(pdf, result)
        check_annotations(pdf, structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["AnnotationCount"] >= 1
    assert result["AnnotationsFound"] is True
    assert result["LinkAnnotationCount"] >= 1
    assert result["LinkStructureCount"] >= 1
    assert result["TaggedAnnotationsTest"] == "Pass"
    assert result["Accessible"] is True


# Tagged PDF with an external URI link: count as external link annotation
def test_check_annotations_counts_external_uri_links(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = (
        fixtures_dir / FIXTURE_SUBDIR / "annotations_tagged_external_link_pass.pdf"
    )
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_annotation_inputs(pdf, result)
        check_annotations(pdf, structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["LinkAnnotationCount"] >= 1
    assert result["ExternalLinkAnnotationCount"] >= 1
    assert result["InternalLinkAnnotationCount"] == 0
    assert result["AnnotationPagesWithLinks"] >= 1
    assert result["TaggedAnnotationsTest"] == "Pass"
    assert result["Accessible"] is True


# Tagged PDF with an internal destination link: count as internal link annotation
def test_check_annotations_counts_internal_destination_links(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = (
        fixtures_dir / FIXTURE_SUBDIR / "annotations_tagged_internal_link_pass.pdf"
    )
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_annotation_inputs(pdf, result)
        check_annotations(pdf, structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["LinkAnnotationCount"] >= 1
    assert result["InternalLinkAnnotationCount"] >= 1
    assert result["AnnotationPagesWithLinks"] >= 1
    assert result["TaggedAnnotationsTest"] == "Pass"
    assert result["Accessible"] is True


# Tagged PDF with links on more than one page: count distinct pages with links
def test_check_annotations_counts_pages_with_links(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = (
        fixtures_dir / FIXTURE_SUBDIR / "annotations_tagged_links_two_pages_pass.pdf"
    )
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_annotation_inputs(pdf, result)
        check_annotations(pdf, structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["LinkAnnotationCount"] >= 2
    assert result["AnnotationPagesWithLinks"] >= 2
    assert result["TaggedAnnotationsTest"] == "Pass"
    assert result["Accessible"] is True


# Tagged PDF with a widget annotation: inventory should detect widget subtype
def test_check_annotations_detects_widget_annotation_in_tagged_pdf(
    fixtures_dir: Path,
    make_result,
):
    pdf_path = fixtures_dir / FIXTURE_SUBDIR / "annotations_tagged_widget_na.pdf"
    result = make_result(pdf_path.name)

    with open_pdf(pdf_path) as pdf:
        structure_items = build_annotation_inputs(pdf, result)
        check_annotations(pdf, structure_items, result)

    assert result["TaggedTest"] == "Pass"
    assert result["AnnotationCount"] >= 1
    assert result["AnnotationsFound"] is True
    assert result["WidgetAnnotationCount"] >= 1
    assert result["LinkAnnotationCount"] == 0
    assert result["TaggedAnnotationsTest"] == "NotApplicable"
    assert result["Accessible"] is True
