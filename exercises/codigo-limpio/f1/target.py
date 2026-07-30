"""Solucion de referencia del ejercicio F1: un solo argumento."""


def crear_evento(datos: dict) -> dict:
    evento = dict(datos)
    evento['agotado'] = datos['capacidad'] == 0
    return evento
