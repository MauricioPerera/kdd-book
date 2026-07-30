"""Punto de partida G12: sobra un import y sobra una variable."""

import json


def cupos_libres(capacidad, inscriptos):
    margen = capacidad * 2
    return max(0, capacidad - inscriptos)
