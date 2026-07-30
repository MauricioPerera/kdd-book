"""Solucion F3: dos funciones con nombre, ningun indicador."""


def formatear_titulo(nombre: str) -> str:
    return nombre.strip()


def formatear_titulo_destacado(nombre: str) -> str:
    return formatear_titulo(nombre).upper()
