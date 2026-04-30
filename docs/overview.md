# simplA11yPDFCrawler — Developer Overview

> A two-phase tool for discovering and auditing the accessibility of PDF and office documents on public-sector websites, used by the Luxembourg Government's Information and Press Service (SIP) for compliance with EU Commission Decision 2018/1524.

---

## Table of Contents

1. [What This App Does](#1-what-this-app-does)
2. [Top-Level Architecture](#2-top-level-architecture)
3. [Key Folders and Responsibilities](#3-key-folders-and-responsibilities)
4. [Main Runtime and Dependencies](#4-main-runtime-and-dependencies)
5. [How Configuration Works](#5-how-configuration-works)
6. [How Data Flows Through the System](#6-how-data-flows-through-the-system)
7. [Entry Points](#7-entry-points)
8. [Tests, Build, and Deployment](#8-tests-build-and-deployment)
9. [Where to Start Reading](#9-where-to-start-reading)

---

## 1. What This App Does

**simplA11yPDFCrawler** performs simplified accessibility audits of documents published on public-sector websites. Given a list of domain names, it:

1. **Crawls** each website with a Scrapy spider, following links and downloading every document it finds (PDF, DOCX, PPTX, XLSX, ODT, ODS, ODP, EPUB, and legacy Office formats).
2. **Analyzes** each downloaded PDF against a set of accessibility rules drawn from the Matterhorn Protocol and WCAG 2.1, then outputs structured results.
3. **Aggregates** per-file results into per-site summary statistics for reporting.

The accessibility checks cover the following categories:

| Category | What is checked |
|---|---|
| Document | Tagging, title, language, bookmarks, protection, text presence, XMP metadata, exemption date |
| Forms | AcroForm and XFA detection, field descriptions, form field tagging |
| Annotations | Link and widget annotation inventory, tagged annotations |
| Alternate Text | Figure alt text, nested alt text, hides-annotation patterns |
| Images | Image XObject detection (fallback for untagged PDFs) |
| Headings | Heading hierarchy: skipped levels, plain `H` tags, first-level requirements |
| Lists | List structure: `L`/`LI`/`LBody` relationships, invalid parents |
| Tables | Table structure: `TR`/`TH`/`TD` hierarchy, headers, row/column regularity |

---

## 2. Top-Level Architecture

The system is built from three cooperating components:

```
list-sites.txt
      │
      ▼
 ┌──────────┐        crawled_files/
 │ crawl.sh │──────► {domain}/
 │ (Bash)   │        *.pdf *.docx …
 └──────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ analyse.sh   │
                    │ (Bash)       │
                    └──────┬───────┘
                           │
              ┌────────────┼──────────────┐
              ▼            ▼              ▼
        pdfCheck.py   file counts    docAnalysis.js
        (Python CLI)  (shell awk)    (Node.js)
              │            │              │
              ▼            ▼              ▼
        out/pdfCheck  out/distribu-  out/office-
           .csv         tion.csv      files.json
```

**Python** handles the heavy PDF processing. `pdfCheck.py` is a thin Typer CLI that delegates to the `scanner/` package, which contains all accessibility check logic.

**Bash** orchestrates the two phases, manages directories, handles timeouts, and builds the distribution CSV with `awk`.

**Node.js** performs the final CSV-to-JSON aggregation step.

---

## 3. Key Folders and Responsibilities

```
simplA11yPDFCrawler/
├── pdfCheck.py          # Typer CLI: tocsv, tojson, tojsonreport subcommands
├── pdf_spider.py        # Scrapy spider: crawls sites, downloads documents
├── docAnalysis.js       # Post-processor: aggregates per-file CSV into per-site JSON
├── crawl.sh             # Phase 1 driver: iterates sites, invokes Scrapy with timeout
├── analyse.sh           # Phase 2 driver: iterates PDFs, runs pdfCheck, calls Node aggregator
├── requirements.txt     # Python dependencies
├── package.json         # Node.js dependencies
│
├── scanner/             # Core PDF accessibility scanner (Python package)
│   ├── scanner.py       # Orchestrates all checks for one PDF file
│   ├── constants.py     # OUTPUT_FIELDS list and DEADLINE_DATE_STR
│   ├── models.py        # StructureItem dataclass
│   ├── dates.py         # PDF and general date parsing helpers
│   ├── image_detection.py  # Image XObject detection
│   ├── report.py        # Structured JSON report builder (ReportRule, build_json_report)
│   ├── structure.py     # Structure tree traversal helpers (safe_name, as_kids, obj_get)
│   ├── text_analysis.py # Text object and font detection
│   └── checks/          # One module per check category
│       ├── document.py  # Tagging, title, language, bookmarks, protection, text
│       ├── figures.py   # Figure alt text
│       ├── alt_text.py  # Nested alt text, hides-annotation
│       ├── annotations.py  # Annotation and link inventory
│       ├── forms.py     # AcroForm, XFA, form field descriptions
│       ├── headings.py  # Heading hierarchy
│       ├── lists.py     # List structure
│       └── tables.py    # Table structure
│
├── tests/               # pytest suite
│   ├── conftest.py      # Shared fixtures (fixtures_dir, make_result)
│   ├── fixtures/        # Real PDF fixtures, one subdirectory per check category
│   └── test_check_*.py  # One test file per check category + test_report_json.py
│
├── crawled_files/       # Runtime: downloaded documents, one sub-dir per domain
├── out/                 # Runtime: analysis results (CSV, JSON)
└── docs/                # Project documentation
```

### scanner/

**`scanner.py`** — The public entry point for the Python API. The `check_file(path, site, debug)` function opens a PDF with pikepdf, calls every check function in `scanner/checks/`, and returns a flat result dict. `init_result()` initializes the result dict with all `OUTPUT_FIELDS` set to `None` and defaults (`Accessible=True`, `Exempt=False`).

**`constants.py`** — Defines `DEADLINE_DATE_STR` (the 2018-09-23 legal exemption cutoff) and `OUTPUT_FIELDS`, the ordered list of all 60+ result keys.

**`models.py`** — The `StructureItem` dataclass. Represents one node from a pre-order traversal of the PDF structure tree: tag type, depth, alt text, ancestor/child type info, and attributes. Many check functions receive a flat `list[StructureItem]` rather than navigating the tree themselves.

**`structure.py`** — Helpers for safely reading pikepdf objects: `safe_name()`, `obj_get()`, and `as_kids()` (normalizes `/K`, which can be a single item, a list, or an MCID integer).

**`dates.py`** — Two parsers: `extract_pdf_date()` handles the PDF-format date string with malformed timezone variants; `extract_date()` is a general fallback using `dateparser`.

**`image_detection.py`** — Lightweight pre-pass: inspects every page's `/Resources /XObject` dictionary to count image XObjects before the structure walk.

**`report.py`** — `ReportRule` (a frozen dataclass) ties a category name, rule name, description, resolver function, and a `compat_only` flag together. `build_json_report()` evaluates every rule against the flat result dict and returns a structured report dict with `Summary`, `Detailed Report`, and `PDF Metadata` sections.

**`text_analysis.py`** — Scans content streams for text operators and font names. `init_analysis()` / `merge_analyses()` aggregate results across pages.

### scanner/checks/

Each module exports one or more `check_*` functions. They all accept the pikepdf PDF object or pre-computed data plus the mutable result dict, and they write their findings directly into that dict.

| Module | Key functions |
|---|---|
| `document.py` | `check_tagging`, `check_empty_text`, `check_metadata_and_title`, `check_language`, `check_bookmarks`, `check_protection` |
| `figures.py` | `check_figures` |
| `alt_text.py` | `check_nested_alt_text`, `check_hides_annotation` |
| `annotations.py` | `check_annotations` |
| `forms.py` | `check_forms` |
| `headings.py` | `check_headings` |
| `lists.py` | `check_lists` |
| `tables.py` | `check_tables` |

### Other top-level files

**`pdfCheck.py`** — A 79-line Typer CLI that imports `scanner.scanner.check_file` and `scanner.report.build_json_report`. It provides three subcommands (`tocsv`, `tojson`, `tojsonreport`) and handles debug-field stripping and CSV append logic.

**`pdf_spider.py`** — The Scrapy spider class `pdf_a11y`. Starts from a seed URL, recursively follows HTML links within the same domain, filters links by file extension, skips search-result pages, and writes downloaded files to `crawled_files/{netloc}/`.

**`docAnalysis.js`** — Reads `pdfCheck.csv` and `distribution.csv` via `csv-parse`, groups rows by site, computes summary statistics, and writes `out/office-files.json`.

---

## 4. Main Runtime and Dependencies

### Python (≥ 3.x, with virtual environment)

| Package | Role |
|---|---|
| `scrapy` | Web crawling framework |
| `pikepdf (~=10.5)` | Primary PDF reader: metadata, structure tree, encryption flags |
| `pdfminer.six` | Secondary PDF reader: content-stream parsing (text / font detection) |
| `langcodes` | BCP-47 language tag validation |
| `dateparser` | Robust date parsing with timezone handling |
| `bitstring` | Bitwise decoding of PDF encryption permission flags |
| `typer` | CLI interface for `pdfCheck.py` |
| `pytest` | Test runner |

### Node.js

| Package | Role |
|---|---|
| `csv-parse` | CSV reading in `docAnalysis.js` |

### System tools

- `bash` — orchestration scripts
- `timeout` (Linux) / `gtimeout` via coreutils (macOS) — 4-hour crawl timeout
- `awk` — file-count statistics in `analyse.sh`
- `node` — report aggregation

---

## 5. How Configuration Works

There are no configuration files. The tool is configured through three mechanisms:

**1. Input file — `list-sites.txt`**
One bare domain per line (no `https://`, no trailing slash).

```
gouvernement.lu
sip.gouvernement.lu
```

**2. Hard-coded constants (intentional)**

| Constant | Location | Value |
|---|---|---|
| Exemption deadline | `scanner/constants.py` | `2018-09-23T00:00:00+02:00` |
| Crawl timeout | `crawl.sh` | 4 hours |
| Download delay | `pdf_spider.py` | 1 second |
| Long-document threshold | `scanner/checks/document.py` | 20 pages |
| Supported extensions | `pdf_spider.py` | pdf, docx, pptx, xlsx, doc, ppt, xls, epub, odt, ods, odp |

**3. CLI arguments**
`pdfCheck.py` accepts `site` and `inputfile` per invocation. `--debug` enables additional output columns (`_log`, `fonts`, `numTxtObjects`). `tojsonreport` also accepts `--compatible` for industry-standard report shape compatibility.

---

## 6. How Data Flows Through the System

### Phase 1 — Crawl

1. `crawl.sh` reads `list-sites.txt` and iterates over domains.
2. For each domain, Scrapy starts `pdf_a11y` at `https://{domain}`.
3. The spider's `parse()` method inspects every response:
   - Document extension → `save_pdf()` writes the file to `crawled_files/{domain}/{filename}`.
   - Otherwise → follow all same-domain `<a href>` links recursively.

### Phase 2 — Analyze

1. `analyse.sh` uses `find` to enumerate every `.pdf` file under `crawled_files/`.
2. For each PDF, it calls `python pdfCheck.py tocsv {site} {path}`, which:
   - Calls `check_file()` in `scanner/scanner.py`.
   - `check_file()` opens the PDF with pikepdf, runs all check functions, and returns a flat result dict.
   - The CLI appends one CSV row to `out/pdfCheck.csv`.
3. `analyse.sh` counts files per site and writes `out/distribution.csv`.
4. `node docAnalysis.js` reads both CSVs, groups by site, computes statistics, and writes `out/office-files.json`.

### Inside check_file()

The scanner runs checks in this order:

1. **Document-level** — tagging, protection, title/metadata, language, text presence, bookmarks. These short-circuit-safe (a broken or encrypted file sets `BrokenFile=True` and returns early).
2. **Image pre-pass** — counts image XObjects and pages containing images.
3. **Structure tree walk** — traverses the PDF structure tree into a flat `list[StructureItem]` in pre-order.
4. **Structure-dependent checks** — figures, nested alt text, hides-annotation, annotations, forms, headings, lists, tables. All receive the same flat list, so the tree is only walked once.
5. **Accessible / TotallyInaccessible flags** — computed last from the accumulated result fields.

### Output Schema

**`out/pdfCheck.csv`** — One row per PDF, 60+ columns (more in `--debug` mode). Key fields:

| Column | Description |
|---|---|
| `Site` | Domain name |
| `File` | Path to the PDF |
| `Accessible` | `False` if any failing test |
| `TotallyInaccessible` | `True` for critical failures (no tags + no text, or protected) |
| `BrokenFile` | `True` if pikepdf could not open the file |
| `TaggedTest` | Structure tree present |
| `EmptyTextTest` | Selectable text detectable |
| `ProtectedTest` | Accessibility permissions not blocked |
| `TitleTest` | Title present and set to display |
| `LanguageTest` | Valid BCP-47 language tag |
| `BookmarksTest` | Bookmarks present for long docs (>20 pages) |
| `Exempt` | Created before the 2018 legal deadline |
| `FormsTest` | Form fields have descriptions |
| `TaggedFormFieldsTest` | Form fields appear tagged |
| `TaggedAnnotationsTest` | Link annotations have corresponding link structure |
| `FiguresAltTextTest` | Figure elements have `/Alt` text |
| `NestedAltTextTest` | No nested alt text |
| `HidesAnnotationTest` | No annotation-hiding alt text patterns |
| `HeadingsTest` | Valid heading hierarchy |
| `ListsTest` | Valid list structure |
| `TablesTest` | Valid table structure |
| `Pages`, `PDFVersion`, `Creator`, `Producer` | Document metadata |
| ... many more granular count and flag fields | See README for full schema |

**`out/office-files.json`** — One object per site with aggregated statistics: `files`, `pdf`, `pdf-exempt`, `pdf-non-exempt`, `pdf-form`, `pdf-blocking-pb-access`, `pcent-pdf`, `pcent-form`, `pcent-pdf-blocking-pb-access`.

---

## 7. Entry Points

| Entry Point | How to Run | Purpose |
|---|---|---|
| `crawl.sh` | `bash crawl.sh` | Phase 1: crawl all sites in `list-sites.txt` |
| `analyse.sh` | `bash analyse.sh` | Phase 2: analyze all downloaded PDFs |
| `pdfCheck.py tocsv` | `python pdfCheck.py tocsv <site> <path>` | Analyze a single PDF, append CSV row |
| `pdfCheck.py tojson` | `python pdfCheck.py tojson <path>` | Analyze a single PDF, print flat JSON |
| `pdfCheck.py tojsonreport` | `python pdfCheck.py tojsonreport <path>` | Analyze a single PDF, print structured report JSON |
| `scanner.scanner.check_file` | Python import | Use the scanner directly from Python code |
| `pytest` | `pytest` | Run the full test suite |
| `docAnalysis.js` | `node docAnalysis.js` | Aggregate existing CSVs into JSON report |

**Typical full run:**
```bash
source env/bin/activate
# edit list-sites.txt with target domains
bash crawl.sh        # can take hours
bash analyse.sh
# results: out/pdfCheck.csv, out/distribution.csv, out/office-files.json
```

**Quick single-file test (flat JSON):**
```bash
source env/bin/activate
python pdfCheck.py tojson /path/to/test.pdf --pretty
```

**Quick single-file test (structured report):**
```bash
python pdfCheck.py tojsonreport /path/to/test.pdf --pretty
python pdfCheck.py tojsonreport /path/to/test.pdf --compatible --pretty
```

**Using the scanner from Python:**
```python
from scanner.scanner import check_file
from scanner.report import build_json_report

result = check_file("path/to/file.pdf")
print(result["Accessible"])

report = build_json_report(result, compatible=False)
print(report["Summary"])
```

---

## 8. Tests, Build, and Deployment

### Tests

The project has a pytest suite under `tests/`. Tests use real PDF fixtures, one subdirectory per check category under `tests/fixtures/`. Each fixture PDF is a minimal example designed to trigger a specific pass, fail, warning, or not-applicable outcome.

```bash
pytest
```

Test files:

| File | What it covers |
|---|---|
| `test_check_tagging.py` | Structure tree presence |
| `test_check_title.py` | Title and DisplayDocTitle |
| `test_check_language.py` | Document language tag |
| `test_check_bookmarks.py` | Bookmarks for long PDFs |
| `test_check_protection.py` | Encryption / permissions |
| `test_check_empty_test.py` | Text presence / image-only |
| `test_check_figures.py` | Figure alt text |
| `test_check_alt_text.py` | Nested alt text, hides-annotation |
| `test_check_annotations.py` | Annotation inventory and tagging |
| `test_check_forms.py` | Form fields and descriptions |
| `test_check_headings.py` | Heading hierarchy |
| `test_check_lists.py` | List structure |
| `test_check_tables.py` | Table structure |
| `test_report_json.py` | Structured report JSON output |

`conftest.py` provides two shared fixtures: `fixtures_dir` (path to `tests/fixtures/`) and `make_result` (factory for an initialized result dict).

### Build

No build step is required. Setup:

```bash
python -m venv env
source env/bin/activate
pip install -r requirements.txt
npm install
```

On macOS, `coreutils` must be installed (`brew install coreutils`) to provide `gtimeout` for the crawl phase.

### Deployment

No CI/CD configuration is present. The tool is designed to run on a developer's machine or a dedicated server as a manual, periodic batch job:

1. Clone repository.
2. Set up environments (`python -m venv env && pip install -r requirements.txt` + `npm install`).
3. Populate `list-sites.txt`.
4. Run `crawl.sh` then `analyse.sh`.
5. Collect output from `out/`.

`crawled_files/`, `out/`, the Python venv, and `node_modules/` are all `.gitignore`d.

---

## 9. Where to Start Reading

If you're new to this codebase, read in this order:

1. **`README.md`** — High-level description, the full test table, installation instructions, and usage examples for every CLI mode.

2. **`crawl.sh`** (≈30 lines) — The simplest file. Shows how domains are iterated, directories created, and Scrapy invoked.

3. **`pdf_spider.py`** (≈70 lines) — The Scrapy spider. Shows how links are discovered, filtered by extension, and files are saved to disk.

4. **`analyse.sh`** (≈50 lines) — Phase 2 orchestration. Shows how it loops over PDFs, calls `pdfCheck.py tocsv`, counts files with awk, and delegates to Node.

5. **`pdfCheck.py`** (≈80 lines) — The CLI wrapper. Shows the three subcommands and how they call into the `scanner` package. Very short — almost all logic lives below.

6. **`scanner/scanner.py`** — The heart of the system. Read `init_result()` to see the full result shape, then `check_file()` to see the order checks are called in and how the structure tree walk feeds into the individual checks.

7. **`scanner/checks/`** — Individual check modules. Start with `document.py` (most foundational), then pick the category you're most interested in. Each module is self-contained and exports one or two functions.

8. **`scanner/report.py`** — The structured report output. See how `ReportRule` resolvers translate the flat result dict into pass/fail/warn/skipped items.

9. **`tests/`** — The test suite is a good way to understand what each check is supposed to do. For any check that's unclear, find the corresponding test file and look at the fixture PDF names — they describe the scenario being tested.

**Key concepts to understand first:**

- The exemption date (2018-09-23) is central — exempt PDFs are excluded from blocking-issue counts.
- `pikepdf` is used for metadata and structure; `pdfminer` is used separately for content-stream scanning (text / font detection).
- The structure tree is walked once into a flat `list[StructureItem]` and shared across all structure-dependent checks.
- The spider only downloads; it does not analyze. Analysis is entirely post-crawl and can be re-run without re-crawling.
- `check_file()` in `scanner/scanner.py` is the Python API — `pdfCheck.py` is just a CLI adapter on top of it.
