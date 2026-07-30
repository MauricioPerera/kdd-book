"""Solucion G12: queda solo lo que se usa."""


def cupos_libres(capacidad, inscriptos):
    return max(0, capacidad - inscriptos)
