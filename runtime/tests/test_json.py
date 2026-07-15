from datetime import datetime

from dateutil.tz import tzutc

from anyforce import json


def test_loads_parses_nested_iso_datetime() -> None:
    decoded = json.loads(
        b'{"date":{"range":["2026-05-31T16:00:00.000Z"]},'
        b'"or":[{"date":{"in":["2026-05-31T16:00:00.000Z"]}}]}'
    )

    assert decoded == {
        "date": {"range": [datetime(2026, 5, 31, 16, tzinfo=tzutc())]},
        "or": [{"date": {"in": [datetime(2026, 5, 31, 16, tzinfo=tzutc())]}}],
    }


def test_loads_keeps_date_only_and_non_datetime_strings() -> None:
    decoded = json.loads(
        b'{"date":"2026-06-01","text":"prefixT2026-05-31T16:00:00.000Z"}'
    )

    assert decoded == {
        "date": "2026-06-01",
        "text": "prefixT2026-05-31T16:00:00.000Z",
    }
