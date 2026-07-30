"""Punto de partida: los errores se tapan."""


def leer_cupos(texto):
    try:
        return int(texto)
    except:
        return 0


def leer_precio(texto):
    try:
        return float(texto)
    except ValueError:
        pass
    return 0.0
