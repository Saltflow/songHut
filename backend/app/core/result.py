from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, TypeVar, Union, Callable, Any

T = TypeVar("T")
E = TypeVar("E")


@dataclass(frozen=True)
class Ok(Generic[T]):
    value: T


@dataclass(frozen=True)
class Err(Generic[E]):
    error: E


Result = Union[Ok[T], Err[E]]


def is_ok(result: Result[T, E]) -> bool:
    return isinstance(result, Ok)


def is_err(result: Result[T, E]) -> bool:
    return isinstance(result, Err)


def ok(value: T) -> Ok[T]:
    return Ok(value)


def err(error: E) -> Err[E]:
    return Err(error)


def unwrap(result: Result[T, E]) -> T:
    match result:
        case Ok(value):
            return value
        case Err(error):
            raise RuntimeError(f"Unwrap on Err: {error}")


def unwrap_or(result: Result[T, Any], default: T) -> T:
    match result:
        case Ok(value):
            return value
        case Err():
            return default


def map_ok(result: Result[T, E], fn: Callable[[T], T2]) -> Result[T2, E]:
    match result:
        case Ok(value):
            return Ok(fn(value))
        case Err():
            return result


def map_err(result: Result[T, E], fn: Callable[[E], E2]) -> Result[T, E2]:
    match result:
        case Ok():
            return result
        case Err(error):
            return Err(fn(error))


def and_then(result: Result[T, E], fn: Callable[[T], Result[T2, E]]) -> Result[T2, E]:
    match result:
        case Ok(value):
            return fn(value)
        case Err():
            return result


def from_optional(value: T | None, error: E) -> Result[T, E]:
    if value is None:
        return Err(error)
    return Ok(value)


def try_result(fn: Callable[..., T], *args: Any, **kwargs: Any) -> Result[T, Exception]:
    try:
        return Ok(fn(*args, **kwargs))
    except Exception as e:
        return Err(e)
