"""Pruebas de reglas de descuento, ahora con aserciones."""

import unittest

from negocio import descuento


class ReglasTest(unittest.TestCase):

    def test_socio(self):
        self.assertEqual(descuento(100, True, False), 15)

    def test_primera_vez(self):
        self.assertEqual(descuento(100, False, True), 10)

    def test_monto_alto(self):
        self.assertEqual(descuento(50000, False, False), 0)
