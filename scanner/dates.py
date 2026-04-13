from datetime import datetime
import re

import dateparser
import pytz
from pikepdf import String
from pikepdf.models.metadata import decode_pdf_date


def extract_date(s: str) -> datetime:
    """Parse a general date string into a timezone-aware datetime.

    Args:
        s: A date string or pikepdf String object in any format recognized by
           dateparser. May be None.

    Returns:
        A timezone-aware datetime (UTC) if parsing succeeds, or None if the
        input is None or cannot be parsed.
    """
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
    """Parse a PDF-format date string into a timezone-aware datetime.

    Handles malformed timezone notations commonly found in PDF metadata
    (e.g. ``+01``, ``+1'0'``, ``+01'00'``, ``+ 1' 0'``) by normalizing them
    to a standard ``+HHMM`` form before decoding. Falls back to
    :func:`extract_date` if pikepdf's decoder raises a ValueError. Attaches
    UTC when the parsed date has no timezone information.

    Args:
        s: A PDF date string or pikepdf String object (typically from
           ``/CreationDate`` or ``/ModDate``). May be None.

    Returns:
        A timezone-aware datetime if parsing succeeds, or None if the input
        is None, empty, or begins with the sentinel string
        ``"CPY Document"``.
    """
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
