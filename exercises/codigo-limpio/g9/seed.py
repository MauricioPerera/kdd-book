"""Punto de partida G9: hay una funcion que ya nadie llama."""

__all__ = ['cupos_libres']


def cupos_libres(capacidad, inscriptos):
    return max(0, capacidad - inscriptos)


def cupos_libres_viejo(capacidad, inscriptos, reservados):
    return capacidad - inscriptos - reservados
