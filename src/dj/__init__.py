import json

from dataclasses import asdict, fields, is_dataclass
from datetime import date
from enum import Enum
from functools import singledispatch
from inspect import signature
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    Mapping,
    MutableMapping,
    Protocol,
    Type,
    TypeVar,
    Union,
    runtime_checkable,
)


class ValidationError(Exception):
    """Validation error for deserializing JSON into dataclasses."""


SIMPLE_TYPES = {str, int, bool, type(None)}


@runtime_checkable
class GenericAlias(Protocol):
    __origin__: Type[Any]
    __args__: Iterable[Any]


class DataClass(Protocol):
    __dataclass_fields__: MutableMapping[str, Any]


def from_json(json_input: str, cls: Any) -> DataClass:
    raw = json.loads(json_input)
    for field in fields(cls):
        raw[field.name] = validate_and_deserialize(
            field.type, raw.get(field.name), field.name
        )

    instance: DataClass = cls(**raw)
    return instance


def to_json(instance: DataClass) -> str:
    return json.dumps(asdict(instance), default=to_serializable)


def to_dict(instance: DataClass) -> Dict[str, Any]:
    return asdict(instance)


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


T = TypeVar("T")


@singledispatch
def _adapt(_to_type: Type[T], value: T, /) -> T:
    return value


Adaptable = Callable[[Any], Any]
Adapted = Callable[[Mapping[str, Any]], Mapping[str, Any]]


def adapt(function: Adaptable) -> Adapted:
    sig = signature(function)
    first_parameter = next(k for k in sig.parameters.keys())
    if not is_dataclass(first_parameter):
        raise TypeError(
            f"{first_parameter} needs to be (type annotated as) a dataclass."
        )

    def wrapper(in_: Mapping[str, Any], /) -> Mapping[str, Any]:
        bound = sig.bind(in_)
        bound.apply_defaults()
        for key, value in bound.arguments.items():
            to_type = sig.parameters[key].annotation
            if is_dataclass(to_type):
                bound.arguments[key] = to_type(**value)
            else:
                bound.arguments[key] = _adapt(to_type, value)

        result = function(bound.args[0])
        return asdict(result)

    return wrapper
