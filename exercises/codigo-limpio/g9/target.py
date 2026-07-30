"""Solucion G9: queda solo lo que se usa."""

__all__ = ['cupos_libres']


def cupos_libres(capacidad, inscriptos):
    return max(0, capacidad - inscriptos)
