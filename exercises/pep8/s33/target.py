"""Carrito."""


class Carrito:
    """Un carrito de compras."""

    def __init__(self, precios):
        self.precios = precios

    def total(self):
        return sum(self.precios)
