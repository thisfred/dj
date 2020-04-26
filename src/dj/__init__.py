import json

from dataclasses import asdict, fields
from datetime import date
from enum import Enum
from functools import singledispatch
from typing import Any, Iterable, Mapping, Protocol, Type, Union, runtime_checkable


class ValidationError(Exception):
    """Validation error for deserializing JSON into dataclasses."""


SIMPLE_TYPES = {str, int, bool, type(None)}


@runtime_checkable
class GenericAlias(Protocol):
    __origin__: Type[Any]
    __args__: Iterable[Any]


class DataClassInstance(Protocol):
    _FIELDS: Mapping[str, Any]  # pylint: disable=unsubscriptable-object


def from_json(json_input: str, cls: Any) -> DataClassInstance:
    raw = json.loads(json_input)
    for field in fields(cls):
        raw[field.name] = validate_and_deserialize(
            field.type, raw.get(field.name), field.name
        )

    instance: DataClassInstance = cls(**raw)
    return instance


def to_json(instance: DataClassInstance) -> str:
    return json.dumps(asdict(instance), default=to_serializable)


@singledispatch
def to_serializable(value: Any, /) -> str:
    """
    Neat trick copied from Hynek Schlawack's blog post:

    https://hynek.me/articles/serialization/
    """
    return str(value)


@to_serializable.register
def serialize_date(value: date, /) -> str:
    return value.isoformat()


@to_serializable.register
def serialize_enum(enum: Enum, /) -> Union[str, int]:
    result: Union[str, int] = enum.value
    return result


def validate_and_deserialize(  # noqa
    field_type: Any, value: Any, field_name: str
) -> Any:
    # This has a high cyclomatic complexity, but splitting it up would lead to more
    # indirection than this short function merits. Will revisit as it grows.
    if field_type in SIMPLE_TYPES:
        if isinstance(value, field_type):
            return value

    if field_type is date:
        return date.fromisoformat(value)

    if isinstance(field_type, GenericAlias):
        if field_type.__origin__ == Union:
            for possible_type in field_type.__args__:
                try:
                    return validate_and_deserialize(possible_type, value, field_name)
                except ValidationError:
                    continue

    try:
        if issubclass(field_type, Enum):
            return field_type(value)

    except TypeError:
        pass

    raise ValidationError(
        f"Field `{field_name}` got value of unexpected type: {type(value)}, should be: "
        f"{field_type}."
    )
