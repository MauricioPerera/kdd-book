"""Solucion G25: cada numero tiene nombre y el nombre explica la regla."""

DIAS_MINIMOS_SIN_RECARGO = 15
FACTOR_RECARGO_TARDIO = 1.35
FACTOR_RECARGO_NORMAL = 1.1
DECIMALES = 2


def precio_con_recargo(base, dias_de_anticipacion):
    if dias_de_anticipacion < DIAS_MINIMOS_SIN_RECARGO:
        return round(base * FACTOR_RECARGO_TARDIO, DECIMALES)
    return round(base * FACTOR_RECARGO_NORMAL, DECIMALES)
