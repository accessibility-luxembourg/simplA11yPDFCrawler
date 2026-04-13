from datetime import datetime
import re

import dateparser
import pytz
from pikepdf import String
from pikepdf.models.metadata import decode_pdf_date


def extract_date(s: str) -> datetime:
    if s is None:
        return None
    if isinstance(s, String):
        s = str(s)
    try:
        return dateparser.parse(
            s,
            settings={"TIMEZONE": "UTC", "RETURN_AS_TIMEZONE_AWARE": True},
        )
    except ValueError:
        return None


def extract_pdf_date(s: str) -> datetime:
    if s is None:
        return None
    if isinstance(s, String):
        s = str(s)
    s = s.strip()
    if len(s) == 0:
        return None
    if s.startswith("CPY Document"):
        return None

    # manage malformed timezones (ex: +01, +1'0', +01'00', + 1' 0')
    match = re.search(r"\+([\d\':\s]+)$", s)
    if match is not None:
        tz = match.group(0)
        initial_tz = tz
        if len(tz) == 3:
            tz = tz + "00"
        if "'" in tz:
            normalized = re.search(r"\+\s?(\d+)\'\s?(\d+)\'?", tz)
            if normalized is not None:
                tz = "+%02d%02d" % (int(normalized.group(1)), int(normalized.group(2)))
            else:
                tz = "+0000"
        s = s.replace(initial_tz, tz)
    try:
        pdf_date = decode_pdf_date(s)
        # we add a timezone when it is missing
        # it can of course be inaccurate, but we don't really need a precision < 1 day
        if not (
            pdf_date.tzinfo is not None
            and pdf_date.tzinfo.utcoffset(pdf_date) is not None
        ):
            pdf_date = pdf_date.replace(tzinfo=pytz.utc)
        return pdf_date
    except ValueError:
        return extract_date(s)
