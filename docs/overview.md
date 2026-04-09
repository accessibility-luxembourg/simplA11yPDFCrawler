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

The accessibility checks cover:
- Document tagging (structure tree present)
- Title in metadata and displayed in viewer
- Document language tag (valid BCP-47 code)
- Bookmarks / table of contents for long documents (>20 pages)
- Copy/accessibility permissions (not password-locked against screen readers)
- Presence of actual text vs. scanned image
- Pre-deadline exemption (documents created before 2018-09-23 are exempt under Luxembourg law)
- Form detection (AcroForm and dynamic XFA forms)
- XMP metadata presence

---

## 2. Top-Level Architecture

The system is built from three cooperating components written in three different languages, each chosen for its strengths:

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
        (Python)      (shell awk)    (Node.js)
              │            │              │
              ▼            ▼              ▼
        out/pdfCheck  out/distribu-  out/office-
           .csv         tion.csv      files.json
```

**Python** handles the heavy PDF processing (pikepdf, pdfminer).
**Bash** orchestrates the two phases, manages directories, handles timeouts, and builds the distribution CSV with `awk`.
**Node.js** performs the final CSV-to-JSON aggregation step.

---

## 3. Key Folders and Responsibilities

```
simplA11yPDFCrawler/
├── pdf_spider.py        # Scrapy spider: crawls sites, downloads documents
├── pdfCheck.py          # Core accessibility checker: analyzes each PDF
├── docAnalysis.js       # Post-processor: aggregates per-file CSV into per-site JSON
├── crawl.sh             # Phase 1 driver: iterates sites, invokes Scrapy with timeout
├── analyse.sh           # Phase 2 driver: iterates PDFs, runs pdfCheck, calls Node aggregator
├── requirements.txt     # Python dependencies
├── package.json         # Node.js dependencies
├── crawled_files/       # Runtime output: downloaded documents, one sub-dir per domain
│   └── {domain}/        # e.g., gouvernement.lu/
│       └── *.pdf …
├── out/                 # Runtime output: analysis results
│   ├── pdfCheck.csv     # Per-file accessibility results (appended incrementally)
│   ├── distribution.csv # Per-site total / non-PDF file counts
│   └── office-files.json # Final aggregated report
├── docs/                # Project documentation
└── env/                 # Python virtual environment (not committed)
```

**`pdf_spider.py`** — The Scrapy spider class `pdf_a11y`. Starts from a seed URL, recursively follows HTML links within the same domain (prevents off-domain crawling), filters links by file extension, skips search-result pages (URL pattern match for "recherche"/"search"), and writes downloaded files to `crawled_files/{netloc}/`. A `unique_file()` helper avoids overwriting files with duplicate names.

**`pdfCheck.py`** — The accessibility engine. Exposes a Typer CLI with two subcommands: `tocsv` (append one row to a CSV) and `tojson` (print JSON to stdout). Internally it opens each file with pikepdf, runs all accessibility tests, and returns a flat result dict. Most logic lives in a single `checkPDF()` function with a companion `_getTextObjects()` for content-stream analysis.

**`docAnalysis.js`** — Reads `pdfCheck.csv` and `distribution.csv` via the `csv-parse` library, groups rows by site, computes summary statistics (exempt counts, blocking-issue counts, percentages), and writes `office-files.json`.

**`crawl.sh`** — Reads `list-sites.txt` line by line. For each domain it creates `crawled_files/{domain}/`, then invokes Scrapy under a 4-hour `timeout` (or `gtimeout` on macOS). Logs go to `scrapy.log`.

**`analyse.sh`** — Loops over every PDF found under `crawled_files/`, derives the `site` name from the directory, calls `pdfCheck.py tocsv`, and appends results to `out/pdfCheck.csv`. Then uses shell commands and `awk` to count files per site and write `out/distribution.csv`. Finally runs `node docAnalysis.js`.

---

## 4. Main Runtime and Dependencies

### Python (≥ 3.x, with virtual environment)

| Package | Role |
|---|---|
| `scrapy` | Web crawling framework powering the spider |
| `pikepdf (~=10.5)` | Primary PDF reader: metadata, structure tree, encryption flags |
| `pdfminer.six` | Secondary PDF reader: content-stream parsing (text / font detection) |
| `langcodes` | BCP-47 language tag validation |
| `dateparser` | Robust date parsing with timezone handling |
| `bitstring` | Bitwise decoding of PDF encryption permission flags |
| `typer` | CLI interface for `pdfCheck.py` |

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
One bare domain per line (no `https://`, no trailing slash). This is the only user-supplied input before running.

```
gouvernement.lu
sip.gouvernement.lu
```

**2. Hard-coded constants (intentional)**
Key values are baked into the source:

| Constant | Location | Value |
|---|---|---|
| Exemption deadline | `pdfCheck.py` | `2018-09-23T00:00:00+02:00` |
| Crawl timeout | `crawl.sh` | 4 hours |
| Download delay | `pdf_spider.py` | 1 second |
| Long-document threshold | `pdfCheck.py` | 20 pages |
| Supported extensions | `pdf_spider.py` | pdf, docx, pptx, xlsx, doc, ppt, xls, epub, odt, ods, odp |

**3. CLI arguments**
`pdfCheck.py` accepts `site` and `pdf_path` arguments for each invocation. Debug mode (`--debug`) enables additional output columns (`_log`, `fonts`, `numTxtObjects`).

---

## 6. How Data Flows Through the System

### Phase 1 — Crawl

1. `crawl.sh` reads `list-sites.txt` and iterates over domains.
2. For each domain, Scrapy starts `pdf_a11y` at `https://{domain}`.
3. The spider's `parse()` method inspects every response:
   - If the URL ends with a recognized document extension → `save_pdf()` writes the file to `crawled_files/{domain}/{filename}`.
   - Otherwise → follow all same-domain `<a href>` links recursively.
4. Scrapy respects the 1-second download delay between requests and enforces domain isolation.

### Phase 2 — Analyze

1. `analyse.sh` uses `find` to enumerate every `.pdf` file under `crawled_files/`.
2. For each PDF, it calls `python pdfCheck.py tocsv {site} {path}`, which:
   - Opens the file with pikepdf.
   - Runs all accessibility test functions.
   - Handles errors (corrupt files, password-protected files) gracefully, marking `BrokenFile=True`.
   - Appends one CSV row to `out/pdfCheck.csv`.
3. `analyse.sh` counts files per site and writes `out/distribution.csv`.
4. `node docAnalysis.js` reads both CSVs, groups by site, computes statistics, and writes `out/office-files.json`.

### Output Schema

**`out/pdfCheck.csv`** — One row per PDF, 22 columns (25 in debug mode):

| Column | Description |
|---|---|
| Site | Domain name |
| File | Path to the PDF |
| Accessible | True if no failing tests |
| TotallyInaccessible | True if critical failures (no tags AND no text, or protected) |
| BrokenFile | True if pikepdf could not open the file |
| TaggedTest | Pass/Fail — structure tree present |
| EmptyTextTest | Pass/Fail — text content detectable |
| ProtectedTest | Pass/Fail — accessibility permissions not blocked |
| TitleTest | Pass/Fail — title metadata present and displayed |
| LanguageTest | Pass/Fail — valid BCP-47 language tag |
| BookmarksTest | Pass/Fail — bookmarks present for long docs |
| Exempt | True if created before the 2018 deadline |
| Pages, PDFVersion, Creator, Producer | Document metadata |
| hasXmp, hasTitle, hasDisplayDocTitle, hasLang, InvalidLang, Form, xfa, hasBookmarks | Granular flags |

**`out/office-files.json`** — One object per site with aggregated statistics:
`files`, `pdf`, `pdf-exempt`, `pdf-non-exempt`, `pdf-form`, `pdf-blocking-pb-access`, `pcent-pdf`, `pcent-form`, `pcent-pdf-blocking-pb-access`.

---

## 7. Entry Points

| Entry Point | How to Run | Purpose |
|---|---|---|
| `crawl.sh` | `bash crawl.sh` | Phase 1: crawl all sites in `list-sites.txt` |
| `analyse.sh` | `bash analyse.sh` | Phase 2: analyze all downloaded PDFs |
| `pdfCheck.py tocsv` | `python pdfCheck.py tocsv <site> <path>` | Analyze a single PDF, append CSV row |
| `pdfCheck.py tojson` | `python pdfCheck.py tojson <site> <path>` | Analyze a single PDF, print JSON |
| `docAnalysis.js` | `node docAnalysis.js` | Aggregate existing CSVs into JSON report |

**Typical full run:**
```bash
# 1. Activate Python environment
source env/bin/activate

# 2. Edit list-sites.txt with target domains

# 3. Crawl (can take hours)
bash crawl.sh

# 4. Analyze all PDFs
bash analyse.sh

# Results: out/pdfCheck.csv, out/distribution.csv, out/office-files.json
```

**Quick single-file test:**
```bash
source env/bin/activate
python pdfCheck.py tojson example.lu /path/to/test.pdf
```

---

## 8. Tests, Build, and Deployment

### Tests

There is no formal test suite. Correctness is validated operationally:
- Running `pdfCheck.py tojson` against a known PDF and inspecting the output.
- Running the full `analyse.sh` pipeline on a small `crawled_files/` directory and verifying `pdfCheck.csv`.
- The `--debug` flag on `pdfCheck.py` exposes additional columns (`_log`, `fonts`, `numTxtObjects`) useful for troubleshooting edge cases.

### Build

No build step is required. Setup is:

```bash
# Python environment
python -m venv env
source env/bin/activate
pip install -r requirements.txt

# Node.js
npm install
```

On macOS, `coreutils` must be installed (`brew install coreutils`) to provide `gtimeout` for the crawl phase.

### Deployment

No CI/CD configuration is present (no GitHub Actions, Dockerfile, or Makefile). The tool is designed to run on a developer's machine or a dedicated server as a manual, periodic batch job:

1. Clone repository.
2. Set up environments (Python venv + npm install).
3. Populate `list-sites.txt`.
4. Run `crawl.sh` then `analyse.sh`.
5. Collect output from `out/`.

The `crawled_files/` and `out/` directories, the Python venv, and `node_modules/` are all `.gitignore`d.

---

## 9. Where to Start Reading

If you're new to this codebase, read in this order:

1. **`README.md`** — High-level description, installation instructions, and usage examples. Covers the macOS vs Linux difference for `timeout`.

2. **`crawl.sh`** (≈30 lines) — The simplest file. See how domains are iterated, directories created, and Scrapy invoked. Immediately shows the two-phase structure.

3. **`pdf_spider.py`** (≈70 lines) — The Scrapy spider class. See how links are discovered, filtered by extension, and how files are saved to disk. Small, self-contained, easy to follow.

4. **`analyse.sh`** (≈50 lines) — Phase 2 orchestration. See how it loops over PDFs, calls `pdfCheck.py`, counts files with awk, and delegates to Node.

5. **`pdfCheck.py`** — The heart of the system. Start with the Typer CLI entrypoints (`toCSV`, `toJSON`) at the bottom of the file to see what's called, then work upward through `checkPDF()` and the individual test functions. The most complex logic is in `_getTextObjects()` (content-stream analysis) and the encryption permission check (`ProtectedTest`).

6. **`docAnalysis.js`** — The final aggregation step. Short and straightforward once you understand the CSV schema from `pdfCheck.py`.

**Key concepts to understand first:**
- The exemption date (2018-09-23) is central to many output fields — exempt PDFs are excluded from blocking-issue counts.
- `pikepdf` is used for metadata and structure; `pdfminer` is used separately for content-stream scanning.
- The spider only downloads; it does not analyze. Analysis is entirely post-crawl and can be re-run without re-crawling.
