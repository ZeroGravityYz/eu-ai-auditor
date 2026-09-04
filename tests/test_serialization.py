import json

import numpy as np
import pandas as pd

from eu_ai_auditor.serialization import json_compatible


def test_json_compatible_produces_strict_json_for_scientific_values():
    value = {
        "nan": np.nan,
        "positive_infinity": np.float64(np.inf),
        "missing": pd.NA,
        "boolean": np.bool_(True),
        "integer": np.int64(4),
    }

    payload = json.dumps(json_compatible(value), allow_nan=False)

    assert json.loads(payload) == {
        "nan": None,
        "positive_infinity": None,
        "missing": None,
        "boolean": True,
        "integer": 4,
    }
