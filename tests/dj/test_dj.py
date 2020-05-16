import json

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Optional

from pytest import fixture, raises

from dj import ValidationError, adapt, from_json, to_dict, to_json


class ReleaseType(Enum):
    lp = "lp"
    cd = "cd"
    download = "download"


@dataclass
class Record:
    artist: str
    title: str
    release_type: Optional[ReleaseType] = None
    release_date: Optional[date] = None
    notes: Optional[str] = None


@dataclass
class Response:
    message: str


@fixture
def a_record() -> Record:
    return Record(
        artist="Waxahatchee",
        title="St. Cloud",
        release_date=date(2020, 3, 27),
        release_type=ReleaseType.lp,
    )


@fixture
def an_lp() -> Record:
    return Record(artist="Destroyer", title="Have We Met", release_type=ReleaseType.lp)


def is_lp(record: Record) -> Response:
    if record.release_type and record.release_type == ReleaseType.lp:
        return Response("Success!")

    return Response("Failure")


adapted = adapt(is_lp)


def test_roundtrip(a_record):
    assert from_json(to_json(a_record), Record) == a_record


def test_raises_nice_exceptions(a_record):
    broken_record = json.loads(to_json(a_record))
    broken_record["title"] = 12

    with raises(ValidationError, match="title"):
        from_json(json.dumps(broken_record), Record)


def test_adapt_takes_dictionary(an_lp):
    lp_as_dict = to_dict(an_lp)
    result = adapted(lp_as_dict)
    assert result["message"] == "Success!"
