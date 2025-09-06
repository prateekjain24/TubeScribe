from __future__ import annotations

"""Engines package: interface registry and helpers.

Concrete engines (e.g., Whisper) should:
- define a unique `name` attribute
- implement the `TranscriptionEngine` Protocol (see `base.py`)
- be registered via the `@register_engine` decorator
"""

from typing import Dict, Type, Any


_ENGINES: Dict[str, Type[Any]] = {}


def register_engine(cls: Type[Any]) -> Type[Any]:
    name = getattr(cls, "name", None)
    if not name or not isinstance(name, str):
        raise ValueError("Engine class must define a string `name` attribute")
    _ENGINES[name] = cls
    return cls


def available_engines() -> list[str]:
    return sorted(_ENGINES)


def get_engine_class(name: str) -> Type[Any]:
    try:
        return _ENGINES[name]
    except KeyError as e:
        raise KeyError(f"unknown engine '{name}'") from e


def create_engine(name: str):
    cls = get_engine_class(name)
    return cls()  # type: ignore[call-arg]


__all__ = [
    "register_engine",
    "available_engines",
    "get_engine_class",
    "create_engine",
]

