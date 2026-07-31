"""Carrito."""


class Carrito:
    """Un carrito de compras."""

    def __init__(este, precios):
        este.precios = precios

    def total(este):
        return sum(este.precios)
