"""Punto de partida F3: un booleano decide que hace la funcion."""


def formatear_titulo(nombre, en_mayusculas=False):
    if en_mayusculas:
        return nombre.strip().upper()
    return nombre.strip()
