# simplA11yPDFCrawler

simplA11yReport is a tool supporting the simplified accessibility monitoring method as described in the [commission implementing decision EU 2018/1524](https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32018D1524&from=EN). It is used by [SIP (Information and Press Service)](https://sip.gouvernement.lu/en.html) in Luxembourg to monitor the websites of public sector bodies.

The tool can be used in two ways:

1. **Crawler workflow**: crawl a list of websites, download documents, analyze all PDFs, and generate CSV/JSON output.
2. **Single-PDF workflow**: run the PDF checker directly against an individual PDF and return either raw JSON or a structured accessibility report.

The generated files can be used by [simplA11yGenReport](https://github.com/accessibility-luxembourg/simplA11yGenReport) to give an overview of the state of document accessibility on controlled websites.

Most of the [accessibility reports (in french)](https://data.public.lu/fr/datasets/audits-simplifies-de-laccessibilite-numerique-2020-2021/) published by SIP on [data.public.lu](https://data.public.lu) have been generated using [simplA11yGenReport](https://github.com/accessibility-luxembourg/simplA11yGenReport) and data coming from this tool.

## PDF accessibility tests

The checker runs document-level tests, structure-tree tests, annotation tests, form tests, figure/alt-text tests, heading tests, list tests and table tests.

| Category       | Test                    | Description                                                                                                                              |
| -------------- | ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| Document       | `EmptyTextTest`         | Checks whether the file appears to contain real text or only images. This can detect scanned/image-only PDFs without OCR.                |
| Document       | `TaggedTest`            | Checks whether the document has a PDF structure tree and is marked as tagged.                                                            |
| Document       | `ProtectedTest`         | Checks whether document permissions block access by assistive technologies.                                                              |
| Document       | `TitleTest`             | Checks whether the PDF has a title and whether the title is configured to display in the PDF reader title bar.                           |
| Document       | `LanguageTest`          | Checks whether the PDF has a valid default language.                                                                                     |
| Document       | `BookmarksTest`         | Checks whether PDFs longer than 20 pages have bookmarks.                                                                                 |
| Document       | `hasXmp`                | Checks whether XMP metadata is present.                                                                                                  |
| Document       | `Exempt`                | Estimates whether the document is outside the legal scope based on its creation/modification date.                                       |
| Forms          | `FormsTest`             | Checks whether interactive form fields have descriptions.                                                                                |
| Forms          | `TaggedFormFieldsTest`  | Checks whether interactive form fields appear to be tagged or structurally represented. This is a structural approximation.              |
| Forms          | `Form`                  | Detects whether the PDF contains AcroForm fields.                                                                                        |
| Forms          | `xfa`                   | Detects dynamic XFA forms.                                                                                                               |
| Annotations    | `TaggedAnnotationsTest` | Checks link annotations against link structure elements. This is a structural approximation.                                             |
| Annotations    | annotation inventory    | Counts annotations, link annotations, widget annotations, internal links and external links.                                             |
| Alternate Text | `FiguresAltTextTest`    | Checks whether figure structure elements have `/Alt` text, or only `/ActualText`, or no alternate text.                                  |
| Alternate Text | `NestedAltTextTest`     | Checks for alternate text nested inside another alt-bearing structure element.                                                           |
| Alternate Text | `HidesAnnotationTest`   | Warns when a form structure element has alternate text and an OBJR child, which can hide annotation content from assistive technologies. |
| Images         | image object detection  | Counts image XObjects and pages containing images. Used as a fallback when the PDF is untagged.                                          |
| Headings       | `HeadingsTest`          | Checks heading structure for skipped levels, plain `H` tags, first heading level and missing headings.                                   |
| Lists          | `ListsTest`             | Checks PDF list structure, including `L`, `LI`, `Lbl` and `LBody` relationships.                                                         |
| Tables         | `TablesTest`            | Checks table structure, including `TR`, `TH`, `TD`, headers and table regularity.                                                        |
| Tables         | row/column regularity   | Detects uneven row lengths, including basic `RowSpan` and `ColSpan` handling.                                                            |

### Known limitations

This tool performs automated checks. It does not replace a full manual accessibility audit.

Some issues cannot be reliably verified from automated checks alone, including:

- logical reading order
- color contrast
- full page-content-to-structure association
- multimedia accessibility

## Installation

```bash
git clone https://github.com/accessibility-luxembourg/simplA11yPDFCrawler.git
cd simplA11yPDFCrawler

npm install

python -m venv env # on a Mac, use python3 instead of python
source ./env/bin/activate
pip install -r requirements.txt
mkdir crawled_files ; mkdir out
chmod a+x *.sh
```

On MacOS, the `timeout` or `gtimeout` commands may not be available. You may need to install the coreutils package via `brew`:

```bash
brew install coreutils
```

## Usage: crawl and analyze websites

To crawl websites, store the list of target sites in `list-sites.txt`, one domain per line.

Example:

```text
test.public.lu
etat.public.lu
projects.accesscomputing.uw.edu
```

Then run the workflow in two steps.

### 1. Crawl documents

```bash
./crawl.sh
```

This crawls all sites listed in `list-sites.txt`. Each site is crawled for a maximum of 4 hours by default (it can be adjusted in `crawl.sh`). The resulting files will be placed in the `crawled_files` folder. This step can be quite long.

### 2. Analyze downloaded PDFs

```bash
./analyse.sh
```

This analyses the files and detects accessibility issues. The resulting files will be placed in the `out` folder.

Everytime you come back to the project and start a terminal, you have to load the virtual environment first with the following command:

```bash
source ./env/bin/activate
```

#### Output files

Running `analyse.sh` creates three files in the `out` folder.

<details>
<summary>
<strong>`out/pdfCheck.csv`</strong>
</summary>

<br>
One row per PDF. This is the main per-file scanner output.

Fields include:

| Field                         | Description                                                                                                                     |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `Site`                        | Site/domain associated with the file.                                                                                           |
| `File`                        | PDF filename.                                                                                                                   |
| `Accessible`                  | `False` if the scanner found a failing accessibility issue.                                                                     |
| `TotallyInaccessible`         | `True` if the PDF fails critical access checks, such as being untagged and image-only, or blocking assistive technology access. |
| `BrokenFile`                  | `True` if the PDF could not be opened or parsed.                                                                                |
| `TaggedTest`                  | Whether the PDF is tagged.                                                                                                      |
| `EmptyTextTest`               | Whether text content appears to be present.                                                                                     |
| `ProtectedTest`               | Whether permissions allow assistive technology access.                                                                          |
| `TitleTest`                   | Whether the PDF title exists and is shown in the title bar.                                                                     |
| `LanguageTest`                | Whether the PDF has a valid document language.                                                                                  |
| `BookmarksTest`               | Whether a long PDF has bookmarks.                                                                                               |
| `Exempt`                      | Whether the document appears to predate the legal deadline.                                                                     |
| `Date`                        | Best available creation/modification date.                                                                                      |
| `hasTitle`                    | Whether a title is present.                                                                                                     |
| `hasDisplayDocTitle`          | Whether the Display Document Title flag is set.                                                                                 |
| `hasLang`                     | Whether a document language is present.                                                                                         |
| `InvalidLang`                 | Whether the language tag is invalid.                                                                                            |
| `hasBookmarks`                | Whether bookmarks are present.                                                                                                  |
| `hasXmp`                      | Whether XMP metadata is present.                                                                                                |
| `PDFVersion`                  | PDF version.                                                                                                                    |
| `Creator`                     | Creator software, if available.                                                                                                 |
| `Producer`                    | Producer software, if available.                                                                                                |
| `Pages`                       | Page count.                                                                                                                     |
| `Form`                        | Whether AcroForm fields are present.                                                                                            |
| `xfa`                         | Whether dynamic XFA appears to be present.                                                                                      |
| `FormFieldCount`              | Number of interactive form fields found.                                                                                        |
| `FormFieldSummary`            | Debug-style summary of detected fields.                                                                                         |
| `FormsTest`                   | Whether form fields have descriptions.                                                                                          |
| `FieldsWithoutDescription`    | Fields missing descriptions.                                                                                                    |
| `TaggedFormFieldsTest`        | Whether form fields appear to be tagged or structurally represented.                                                            |
| `UnclearFieldAssociations`    | Field/widget associations that could not be clearly resolved.                                                                   |
| `AnnotationsFound`            | Whether annotations were found.                                                                                                 |
| `AnnotationCount`             | Total number of annotations.                                                                                                    |
| `AnnotationSubtypeCounts`     | Count of annotation subtypes.                                                                                                   |
| `LinkAnnotationCount`         | Number of link annotations.                                                                                                     |
| `WidgetAnnotationCount`       | Number of widget annotations.                                                                                                   |
| `TaggedAnnotationsTest`       | Whether link annotations appear to have corresponding link structure.                                                           |
| `AnnotationSummary`           | Debug-style summary of detected annotations.                                                                                    |
| `LinkStructureCount`          | Number of `Link` structure elements.                                                                                            |
| `ExternalLinkAnnotationCount` | Number of external URI link annotations.                                                                                        |
| `InternalLinkAnnotationCount` | Number of internal destination link annotations.                                                                                |
| `AnnotationPagesWithLinks`    | Number of pages containing link annotations.                                                                                    |
| `HidesAnnotationTest`         | Whether alternate text may hide annotation content.                                                                             |
| `HidesAnnotationIssues`       | Details for hides-annotation warnings.                                                                                          |
| `ImageObjectsFound`           | Number of image XObjects found.                                                                                                 |
| `PagesWithImages`             | Number of pages containing image XObjects.                                                                                      |
| `FiguresFound`                | Number of `Figure` structure elements.                                                                                          |
| `FiguresWithAlt`              | Number of figures with `/Alt`.                                                                                                  |
| `FiguresWithActualTextOnly`   | Number of figures using `/ActualText` but not `/Alt`.                                                                           |
| `FiguresWithoutAlt`           | Number of figures missing alternate text.                                                                                       |
| `FiguresAltTextTest`          | Figure alternate text result.                                                                                                   |
| `NestedAltTextTest`           | Nested alternate text result.                                                                                                   |
| `NestedAltTextIssues`         | Details of nested alternate text issues.                                                                                        |
| `HeadingsTest`                | Heading hierarchy result.                                                                                                       |
| `HeadingCount`                | Number of heading structure elements.                                                                                           |
| `HeadingSequence`             | Heading sequence, such as `H1 > H2 > H3`.                                                                                       |
| `HeadingIssues`               | Heading hierarchy issues.                                                                                                       |
| `ListsTest`                   | List structure result.                                                                                                          |
| `ListCount`                   | Number of list structure elements.                                                                                              |
| `InvalidListItemParents`      | `LI` elements with invalid parents.                                                                                             |
| `InvalidListChildren`         | Unusual or invalid direct list children.                                                                                        |
| `MalformedListNodes`          | Empty or malformed list structures.                                                                                             |
| `TablesTest`                  | Table structure result.                                                                                                         |
| `TableCount`                  | Number of table structure elements.                                                                                             |
| `InvalidTRParents`            | `TR` elements with invalid parents.                                                                                             |
| `InvalidCellParents`          | `TH`/`TD` elements with invalid parents.                                                                                        |
| `TablesWithoutHeaders`        | Tables with no header cells.                                                                                                    |
| `IrregularTables`             | Tables with uneven row/column structure.                                                                                        |

When `--debug` is used, additional debug fields may be included:

| Field           | Description                                            |
| --------------- | ------------------------------------------------------ |
| `_log`          | Internal log of triggered checks and diagnostic notes. |
| `fonts`         | Count of detected fonts.                               |
| `numTxtObjects` | Count of detected text-object operators.               |

</details>

<details>
<summary>
<strong>`out/distribution.csv`</strong>
</summary>

<br>

Summary of file counts per crawled site.

Example:

```csv
site,files,not-pdf
projects.accesscomputing.uw.edu,8,5
```

</details>

<details>
<summary>
<strong>`out/office-files.json`</strong>
</summary>

<br>

Aggregated site-level statistics.

Example:

```json
{
  "example.org": {
    "files": 10,
    "pdf": 4,
    "pdf-exempt": 0,
    "pdf-non-exempt": 4,
    "pdf-form": 1,
    "pdf-blocking-pb-access": 1,
    "pcent-pdf": 40,
    "pcent-form": 10,
    "pcent-pdf-blocking-pb-access": 25
  }
}
```

</details>

## Usage: analyze a single PDF

You can also run the PDF checker directly against one file without crawling a website.

### Raw JSON output

```bash
python pdfCheck.py tojson path/to/file.pdf --pretty
```

With debug fields:

```bash
python pdfCheck.py tojson path/to/file.pdf --debug --pretty
```

The raw JSON output returns the flat internal scanner result, including all individual fields used by the CSV output.

### PDF Accessibility Checker JSON Report

```bash
python pdfCheck.py tojsonreport path/to/file.pdf --pretty
```

The structured accessbility report output groups results into report categories:

- `Summary`
- `Detailed Report`
- `PDF Metadata`

Example shape:

```json
{
  "Summary": {
    "Description": "The checker found no problems in this document.",
    "Needs manual check": 0,
    "Passed manually": 0,
    "Failed manually": 0,
    "Skipped": 0,
    "Passed": 19,
    "Failed": 0
  },
  "Detailed Report": {
    "Document": [],
    "Page Content": [],
    "Forms": [],
    "Alternate Text": [],
    "Tables": [],
    "Lists": [],
    "Headings": []
  },
  "PDF Metadata": {}
}
```

The structured report is intended for applications that want a more human-readable accessibility check, which matches the format of other industry-standard PDF accessibility reports.

#### PDF Accessibility Checker JSON Report: Compatible mode

```bash
python pdfCheck.py tojsonreport path/to/file.pdf --compatible --pretty
```

Compatible mode includes additional rules that this scanner does not fully automate, but which recreates the exact data shape as other industry-standard PDF accessibility reports.

- Unsupported checks like "Tab order" and "Character encodong" are returned as `Skipped`.

- Manual checks like "Logical Reading Order" and "Color contrast" are returned as `Needs manual check`.

This is useful if a consuming application expects the same report categories as other industry-standard PDF accessibility reports.

## Using the checker from Python

The scanner can also be imported and used directly in Python.

```python
from scanner.scanner import check_file

result = check_file("path/to/file.pdf")
print(result["Accessible"])
print(result["TaggedTest"])
```

To produce structured report JSON from Python:

```python
from scanner.scanner import check_file
from scanner.report import build_json_report

result = check_file("path/to/file.pdf")
report = build_json_report(result, compatible=False)

print(report["Summary"])
```

## Project structure

The PDF scanner is split into small modules:

```text
scanner/
  scanner.py              # Orchestrates all checks for one PDF
  constants.py            # Output field definitions
  dates.py                # Date parsing helpers
  image_detection.py      # Image XObject detection
  models.py               # Shared data model
  report.py               # Structured report JSON output
  structure.py            # Structure tree traversal and normalization
  text_analysis.py        # Text/font detection

  checks/
    document.py           # Check metadata, title, tagging, protection, language, bookmarks, text
    figures.py            # Figure and alternate text checks
    headings.py           # Heading hierarchy checks
    lists.py              # List structure checks
    tables.py             # Table structure checks
    forms.py              # AcroForm, XFA and form field checks
    annotations.py        # Annotation and link checks
    alt_text.py           # Nested alt text and hides-annotation checks
```

## Tests

The project includes a pytest suite with example PDF fixtures for every PDF check.

Run tests with:

```bash
pytest
```

The tests cover:

- tagging
- title
- language
- bookmarks
- protection
- empty text / image-only PDFs
- figures and alternate text
- nested alternate text
- hides-annotation patterns
- annotations and links
- forms and field descriptions
- headings
- lists
- tables

The fixture PDFs live under:

```text
tests/fixtures/
```

Each check has targeted pass, fail, warning and not-applicable scenarios where relevant.

## License

This software is developed by the Information and press service of the luxembourgish government and licensed under the MIT license.

This software was initially developed by the [Information and press service](https://sip.gouvernement.lu/en.html) of the Luxembourgish government and licensed under the MIT license.

It was expanded upon by [Bloom Works | Public benefit company](https://www.bloomworks.digital/) with more PDF structure checks, tests, and a new JSON output mode.
