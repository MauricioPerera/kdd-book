"""Solucion F2: devuelve una coleccion nueva y no toca la que recibe."""


def agregar_inscripto(inscriptos: tuple, nombre: str) -> tuple:
    return tuple(inscriptos) + (nombre,)
