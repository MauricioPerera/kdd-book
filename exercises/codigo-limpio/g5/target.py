"""Solucion G5: el calculo vive en un solo lugar."""

ALICUOTA = 0.21


def _total_con_iva(precio, cantidad):
    subtotal = precio * cantidad
    return round(subtotal * (1 + ALICUOTA), 2)


def total_evento(precio, cantidad):
    return _total_con_iva(precio, cantidad)


def total_taller(precio, cantidad):
    return _total_con_iva(precio, cantidad)
