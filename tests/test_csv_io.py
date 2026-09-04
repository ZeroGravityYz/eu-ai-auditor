from io import BytesIO

import pytest

from eu_ai_auditor import read_csv_flexible


def test_read_csv_flexible_detects_semicolon_and_windows_encoding():
    payload = "décision;statut\nprêt;accepté\n".encode("cp1252")

    data = read_csv_flexible(BytesIO(payload))

    assert list(data.columns) == ["décision", "statut"]
    assert data.iloc[0].tolist() == ["prêt", "accepté"]


def test_read_csv_flexible_supports_utf16():
    data = read_csv_flexible("group,outcome\nA,yes\n".encode("utf-16"))

    assert data.to_dict(orient="records") == [{"group": "A", "outcome": "yes"}]


def test_read_csv_flexible_rejects_empty_payload():
    with pytest.raises(ValueError, match="empty|vide"):
        read_csv_flexible(b"")
