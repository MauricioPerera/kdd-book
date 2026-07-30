"""Solucion: cada except dice que atrapa y por que."""


def leer_cupos(texto):
    try:
        return int(texto)
    except ValueError:
        return 0


def leer_precio(texto):
    try:
        return float(texto)
    except ValueError:
        return 0.0
