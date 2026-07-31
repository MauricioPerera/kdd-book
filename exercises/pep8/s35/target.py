"""Reintentos."""

LIMITE_DE_INTENTOS = 3


def quedan(usados):
    return max(0, LIMITE_DE_INTENTOS - usados)
