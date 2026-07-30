"""Oraculo congelado 105: la funcionalidad del proyecto.

Esta sellado y no se toca. El contrato pide agregar aserciones al OTRO archivo
de pruebas, el que si se puede editar.
"""

import unittest

from negocio import descuento


class DescuentoTest(unittest.TestCase):

    def test_socio_y_primera_vez(self):
        self.assertEqual(descuento(100, True, True), 25)

    def test_sin_beneficios(self):
        self.assertEqual(descuento(100, False, False), 0)
