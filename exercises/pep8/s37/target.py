"""Formato de fechas."""

__all__ = ["formatear"]


def formatear(dia, mes):
    return _dos(dia) + "/" + _dos(mes)


def _dos(numero):
    return str(numero).zfill(2)
