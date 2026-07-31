"""Calculo de totales."""

from ayuda import *


def total(precios):
    return redondear(sum(normalizar(p) for p in precios))
