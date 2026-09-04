"""Consistent CSV loading for the web applications and command-line tools."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import pandas as pd


def read_csv_flexible(source: str | Path | bytes | bytearray | BinaryIO) -> pd.DataFrame:
    """Read a CSV with delimiter detection and common research-data encodings.

    The function reads the payload once, then tries Unicode and legacy Western
    European encodings in a deterministic order. It never sends data elsewhere.
    """

    if isinstance(source, (str, Path)):
        payload = Path(source).read_bytes()
    elif isinstance(source, (bytes, bytearray)):
        payload = bytes(source)
    else:
        payload = source.read()
        if isinstance(payload, str):
            payload = payload.encode("utf-8")

    if not payload:
        raise ValueError("Le fichier CSV est vide / The CSV file is empty.")

    errors: list[str] = []
    for encoding in ("utf-8-sig", "utf-16", "cp1252", "latin-1"):
        try:
            return pd.read_csv(BytesIO(payload), sep=None, engine="python", encoding=encoding)
        except (UnicodeError, pd.errors.ParserError) as exc:
            errors.append(f"{encoding}: {exc}")
    detail = errors[-1] if errors else "format inconnu / unknown format"
    raise ValueError(f"CSV illisible / unreadable CSV. {detail}")
