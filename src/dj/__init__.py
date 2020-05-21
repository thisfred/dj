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
    raise NotImplementedError("Register a serializable with @to_serializable.register.")


@to_serializable.register
def serialize_date(value: date, /) -> str:
    return value.isoformat()


@to_serializable.register
def serialize_enum(enum: Enum, /) -> Union[str, int]:
    result: Union[str, int] = enum.value
    return result


A = TypeVar("A")


def identity(value: Any, field_type: Type[A], field_name: str) -> A:
    if isinstance(value, field_type):
        return value

    raise ValidationError(
        f"Field `{field_name}` got value of unexpected type: {type(value)}, should be: "
        f"{field_type}."
    )


def deserialize_date(value: Any, field_type: Type[date], field_name: str) -> date:
    return date.fromisoformat(value)


TYPE_DISPATCH: Dict[Type[Any], Callable[[Any, Type[Any], str], Any]] = {
    str: identity,
    int: identity,
    bool: identity,
    type(None): identity,
    date: deserialize_date,
}


def deserialize_generic_alias(value: Any, field_type: Any, field_name: str) -> Any:
    if field_type.__origin__ != Union:
        raise ValidationError(f"Cannot deserialize fields of type: `{field_type}`")

    errors = []
    for possible_type in field_type.__args__:
        try:
            return validate_and_deserialize(possible_type, value, field_name)
        except ValidationError as e:
            if possible_type is not type(None):  # noqa
                errors.append(e)
            continue

    raise errors[0]


def is_enum(field_type: Any) -> bool:
    return issubclass(field_type, Enum)


T = TypeVar("T")
E = TypeVar("E", bound=Enum)
Enumerable = Callable[[T], E]


def deserialize_enum(value: Any, field_type: Enumerable[T, E]) -> E:
    try:
        return field_type(value)
    except ValueError as e:
        raise ValidationError(*e.args)


def validate_and_deserialize(
    field_type: Any, value: Any, field_name: str
) -> Any:  # noqa
    if field_type in TYPE_DISPATCH:
        return TYPE_DISPATCH[field_type](value, field_type, field_name)

    if isinstance(field_type, GenericAlias):
        return deserialize_generic_alias(value, field_type, field_name)

    assert is_enum(field_type)
    return deserialize_enum(value, field_type)


Adaptable = Callable[[Any], Any]
Adapted = Callable[[Mapping[str, Any]], Mapping[str, Any]]


def adapt(function: Adaptable) -> Adapted:
    sig = signature(function)
    for name, value in sig.parameters.items():
        if not is_dataclass(value.annotation):
            raise TypeError(
                f"Argument `{name}` needs to be (type-annotated as) a dataclass, but "
                f"found `{value.annotation}`."
            )

        def wrapper(in_: Mapping[str, Any], /) -> Mapping[str, Any]:
            bound = sig.bind(in_)
            bound.apply_defaults()
            for key, value in bound.arguments.items():
                to_type = sig.parameters[key].annotation
                bound.arguments[key] = to_type(**value)

            result = function(bound.args[0])
            return asdict(result)

        return wrapper
    else:
        raise TypeError(
            "Can only adapt functions that take a dataclass argument as the first "
            "parameter."
        )
