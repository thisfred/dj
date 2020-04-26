import json

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Optional

from pytest import fixture, raises

from dj import ValidationError, from_json, to_json


class ReleaseType(Enum):
    lp = "lp"
    cd = "cd"
    download = "download"


@dataclass
class Record:
    artist: str
    title: str
    release_type: Optional[ReleaseType]
    release_date: Optional[date]
    notes: Optional[str] = None


@fixture
def a_record() -> Record:
    return Record(
        artist="Waxahatchee",
        title="St. Cloud",
        release_date=date(2020, 3, 27),
        release_type=ReleaseType.lp,
    )


def test_roundtrip(a_record):
    assert from_json(to_json(a_record), Record) == a_record


def test_raises_nice_exceptions(a_record):
    broken_record = json.loads(to_json(a_record))
    broken_record["title"] = 12

    with raises(ValidationError, match="title"):
        from_json(json.dumps(broken_record), Record)
