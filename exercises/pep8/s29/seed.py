"""Contenedor."""

from typing import TypeVar

T = TypeVar("T", covariant=True)


def primero(elementos):
    return elementos[0]
