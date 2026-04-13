import csv
import json
import os

import typer

from scanner.constants import OUTPUT_FIELDS
from scanner.scanner import check_file


app = typer.Typer()

debug = False


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
