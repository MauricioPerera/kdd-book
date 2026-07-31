"""Calculo de totales."""

from ayuda import normalizar, redondear


def total(precios):
    return redondear(sum(normalizar(p) for p in precios))
