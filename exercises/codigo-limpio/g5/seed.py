"""Punto de partida G5: el mismo calculo escrito dos veces."""

ALICUOTA = 0.21


def total_evento(precio, cantidad):
    subtotal = precio * cantidad
    iva = subtotal * ALICUOTA
    return round(subtotal + iva, 2)


def total_taller(precio, cantidad):
    subtotal = precio * cantidad
    iva = subtotal * ALICUOTA
    return round(subtotal + iva, 2)
