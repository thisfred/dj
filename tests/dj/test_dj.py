from dataclasses import dataclass
from datetime import date
from enum import Enum

from dj import from_json, to_json
from pytest import fixture


class ReleaseType(Enum):
    lp = "lp"
    cd = "cd"
    download = "download"


@dataclass
class Record:
    artist: str
    title: str
    release_type: ReleaseType
    release_date: date


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
