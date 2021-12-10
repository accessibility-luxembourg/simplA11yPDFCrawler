# simplA11yPDFCrawler

simplA11yReport is a tool supporting the simplified accessibility monitoring method as described in the [commission implementing decision EU 2018/1524](https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32018D1524&from=EN). It is used by [SIP (Information and Press Service)](https://sip.gouvernement.lu/en.html) in Luxembourg to monitor the websites of public sector bodies.

This tool crawls a list of websites and download all PDF and office documents. Then it analyses the PDF documents and tries to detect accessibility issues.
The generated files can then be used by the tool [simplA11yGenReport](https://github.com/accessibility-luxembourg/simplA11yGenReport) to give an overview of the state of document accessibility on controlled websites.

Most of the [accessibility reports (in french)](https://data.public.lu/fr/datasets/audits-simplifies-de-laccessibilite-numerique-2020-2021/) published by SIP on [data.public.lu](https://data.public.lu) have been generated using [simplA11yGenReport](https://github.com/accessibility-luxembourg/simplA11yGenReport) and data coming from this tool.

## Accessibility Tests

On all PDF files we execute the following tests:

| name | description | WCAG SC | WCAG technique | EN 301 549 | 
|------|-------------|---------|----------------|------------| 
| EmptyText  | does the file contain text or only images? scanned document? | 1.4.5 Image of text (AA)? | PDF 7 |  10.1.4.5 | 
| Tagged | is the document tagged? | | | | 
| Protected | is the document protected and blocks screen readers? | | | |
| hasTitle | Has the document a title? | 2.4.2 Page Titled (A) | PDF 18 | 10.2.4.2 | 
| hasLang | Has the document a default language? | 3.1.1 Language of page (A) | PDF16 | 10.3.1.1 | 
| hasBookmarks | Has the document bookmarks? |  2.4.1 Bypass Blocks (A) | | 10.2.4.1 | 


## Installation

```
git clone https://github.com/accessibility-luxembourg/simplA11yPDFCrawler.git
cd simplA11yPDFCrawler
npm install
pip install -r requirements.txt
mkdir crawled_files ; mkdir out 
```

## Usage

To be able to use this tool, you need a list of websites to crawl. Store this list in a file named `list-sites.txt`, one URL per line. Then the tool is used in two steps:
1. Crawl all the files. Launch the following command `crawl.sh`. It will crawl all the sites mentioned in `list-sites.txt`. Each site is crawled during maximum 4 hours (it can be adjusted in crawl.sh). The resulting files will be placed in the `crawled_files`folder. This step can be quite long.
2. Analyse the files and detect accessibility issues. Launch the command `analyse.sh`. The resulting files will be placed in the `out`folder.


## License
This software is developed by the [Information and press service](https://sip.gouvernement.lu/en.html) of the luxembourgish government and licensed under the MIT license.
