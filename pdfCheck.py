import csv
import json
import os

import typer

from scanner.constants import OUTPUT_FIELDS
from scanner.scanner import check_file

DEBUG_ONLY_FIELDS = ["_log", "fonts", "numTxtObjects"]


app = typer.Typer()


def non_debug_output_fields():
    return [field for field in OUTPUT_FIELDS if field not in DEBUG_ONLY_FIELDS]


@app.command(name="tocsv")
def to_csv(
    site: str,
    inputfile: str,
    outputfile: str = "./out/pdfCheck.csv",
    debug: bool = False,
):
    result = check_file(inputfile, site, debug=debug)

    if debug:
        out_fields = OUTPUT_FIELDS
    else:
        for field in DEBUG_ONLY_FIELDS:
            result.pop(field, None)
        out_fields = non_debug_output_fields()

    csv_exists = os.path.exists(outputfile)
    with open(outputfile, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        if not csv_exists:
            writer.writeheader()
        writer.writerow(result)


@app.command(name="tojson")
def to_json(inputfile: str, debug: bool = False, pretty: bool = False):
    result = check_file(inputfile, debug=debug)
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
