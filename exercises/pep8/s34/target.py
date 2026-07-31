"""Pedido."""


class Pedido:
    """Un pedido en curso."""

    def __init__(self):
        self.items = []

    def agregar_item(self, precio):
        self.items.append(precio)
        return len(self.items)
