import re
import secrets


def normalize_phone(raw):
    """10 digits => +91 is added; otherwise a +countrycode is required.
    Returns '+91XXXXXXXXXX' or None."""
    s = re.sub(r"[\s\-()]", "", raw or "")
    if re.fullmatch(r"[6-9]\d{9}", s):
        s = "+91" + s
    return s if re.fullmatch(r"\+\d{10,14}", s) else None


def make_code():
    return f"{secrets.randbelow(10**6):06d}"
