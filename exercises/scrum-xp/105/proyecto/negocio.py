"""Reglas de descuento del proyecto de ejemplo."""


def descuento(monto, socio, primera_vez):
    """Porcentaje de descuento que corresponde al monto y al comprador."""
    if socio and primera_vez:
        return 25
    if socio:
        return 15
    if primera_vez:
        return 10
    return 0
