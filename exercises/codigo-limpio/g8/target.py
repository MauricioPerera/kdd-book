"""Solucion G8: solo `total` es asunto de quien usa la clase."""


class Inscripcion:
    def __init__(self, precio, cantidad):
        self.precio = precio
        self.cantidad = cantidad

    def _subtotal(self):
        return self.precio * self.cantidad

    def _iva(self):
        return self._subtotal() * 0.21

    def _redondear(self, valor):
        return round(valor, 2)

    def total(self):
        return self._redondear(self._subtotal() + self._iva())
