import json

from dataclasses import asdict, fields
from datetime import date
from enum import Enum
from functools import singledispatch
from typing import Any, Mapping, Protocol, Union


@singledispatch
def to_serializable(val: Any) -> str:
    """
    Neat trick copied from Hynek Schlawack's blog post:

    https://hynek.me/articles/serialization/
    """
    return str(val)


@to_serializable.register
def iso_date_string(value: date, /) -> str:
    return value.isoformat()


@to_serializable.register
def value(enum: Enum) -> Union[str, int]:
    result: Union[str, int] = enum.value
    return result


class DataClassInstance(Protocol):
    _FIELDS: Mapping[str, Any]  # pylint: disable=unsubscriptable-object


def from_json(json_input: str, cls: Any) -> DataClassInstance:
    raw = json.loads(json_input)
    for field in fields(cls):
        if field.type in (str, int, bool):
            assert isinstance(raw[field.name], field.type)
            continue

        if field.type is date:
            raw[field.name] = date.fromisoformat(raw[field.name])
            continue

        if issubclass(field.type, Enum):
            raw[field.name] = field.type(raw[field.name])
            continue

    instance: DataClassInstance = cls(**raw)
    return instance


def to_json(thing: DataClassInstance) -> str:
    return json.dumps(asdict(thing), default=to_serializable)
