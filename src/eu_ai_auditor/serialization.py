"""Strict JSON conversion shared by evidence and research exports."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def json_compatible(value: Any) -> Any:
    """Return a JSON-compatible value with non-finite numbers mapped to null."""

    if isinstance(value, Mapping):
        return {str(key): json_compatible(item) for key, item in value.items()}
    if isinstance(value, pd.DataFrame):
        return json_compatible(value.to_dict(orient="records"))
    if isinstance(value, pd.Series):
        return json_compatible(value.tolist())
    if isinstance(value, np.generic):
        return json_compatible(value.item())
    if value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [json_compatible(item) for item in value]
    if isinstance(value, set):
        return [json_compatible(item) for item in sorted(value, key=str)]
    return value
