"""Punto de partida G8: la clase expone sus tripas."""


class Inscripcion:
    def __init__(self, precio, cantidad):
        self.precio = precio
        self.cantidad = cantidad

    def subtotal(self):
        return self.precio * self.cantidad

    def iva(self):
        return self.subtotal() * 0.21

    def redondear(self, valor):
        return round(valor, 2)

    def total(self):
        return self.redondear(self.subtotal() + self.iva())
