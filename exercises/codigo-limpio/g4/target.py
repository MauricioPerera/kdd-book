"""Solucion G4: no queda ningun aviso silenciado."""

TOPE_DE_CUPOS = 100


def cupos_libres(capacidad, inscriptos):
    return max(0, min(capacidad, TOPE_DE_CUPOS) - inscriptos)
