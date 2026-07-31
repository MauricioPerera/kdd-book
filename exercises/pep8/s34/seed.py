"""Pedido."""


class Pedido:
    """Un pedido en curso."""

    def __init__(self):
        self.Items = []

    def AgregarItem(self, precio):
        self.Items.append(precio)
        return len(self.Items)
