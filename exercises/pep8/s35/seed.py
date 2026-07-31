"""Reintentos."""

limite_de_intentos = 3


def quedan(usados):
    return max(0, limite_de_intentos - usados)
