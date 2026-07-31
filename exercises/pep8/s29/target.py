"""Contenedor."""

from typing import TypeVar

T_co = TypeVar("T_co", covariant=True)


def primero(elementos):
    return elementos[0]
