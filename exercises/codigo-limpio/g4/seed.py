"""Punto de partida G4: los avisos estan apagados en vez de atendidos."""

import json  # noqa: F401

TOPE_DE_CUPOS = 100  # type: ignore


def cupos_libres(capacidad, inscriptos):  # noqa: E501
    return max(0, min(capacidad, TOPE_DE_CUPOS) - inscriptos)
