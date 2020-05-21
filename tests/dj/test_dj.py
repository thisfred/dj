import json

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Any, Callable, Optional

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


@adapt
def is_lp(record: Record) -> Response:
    if record.release_type and record.release_type == ReleaseType.lp:
        return Response("Success!")

    return Response("Failure")


# serialization
def test_to_json(a_record):
    assert (
        to_json(a_record)
        == '{"artist": "Waxahatchee", "title": "St. Cloud", "release_type": "lp", '
        '"release_date": "2020-03-27", "notes": null}'
    )


def test_unknown_types_cannot_be_serialized():
    @dataclass
    class Unserializable:
        callable: Callable[[Any], Any]

    def foo(bar):
        return bar

    unserializable = Unserializable(callable=foo)

    with raises(NotImplementedError, match="Register"):
        to_json(unserializable)


# deserialization
def test_from_json(a_record):
    assert (
        from_json(
            '{"artist": "Waxahatchee", "title": "St. Cloud", "release_type": "lp", '
            '"release_date": "2020-03-27", "notes": null}',
            Record,
        )
        == a_record
    )


def test_validates_enum_membership():
    with raises(ValidationError, match="not a valid ReleaseType"):
        from_json(
            '{"artist": "Waxahatchee", "title": "St. Cloud", "release_type": '
            '"laserdisc", "release_date": "2020-03-27"}',
            Record,
        )


def test_cannot_deserialize_arbitrary_generic_types():
    @dataclass
    class Undeserializable:
        callable: Callable[[Any], Any]

    with raises(ValidationError, match="Cannot deserialize"):
        from_json('{"callable": "foo"}', Undeserializable)


# roundtrip
def test_roundtrip(a_record):
    assert from_json(to_json(a_record), Record) == a_record


# adapt
def test_raises_nice_exceptions(a_record):
    broken_record = json.loads(to_json(a_record))
    broken_record["title"] = 12

    with raises(ValidationError, match="title"):
        from_json(json.dumps(broken_record), Record)


def test_adapt_takes_dictionary(an_lp):
    lp_as_dict = to_dict(an_lp)
    result = is_lp(lp_as_dict)
    assert result["message"] == "Success!"


def test_cannot_adapt_function_that_takes_a_non_dataclass_first_argument():
    with raises(TypeError, match="dataclass"):

        @adapt
        def foo(bar: str) -> Response:
            ...


def test_cannot_adapt_function_that_takes_no_arguments():
    with raises(TypeError, match="dataclass"):

        @adapt
        def foo() -> Response:
            ...
