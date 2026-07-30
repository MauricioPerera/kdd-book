"""Pruebas de reglas de descuento.

Corren y salen en verde, pero no afirman nada: cualquier cambio en `descuento`
las dejaria pasando igual.
"""

import unittest

from negocio import descuento


class ReglasTest(unittest.TestCase):

    def test_socio(self):
        descuento(100, True, False)

    def test_primera_vez(self):
        descuento(100, False, True)

    def test_monto_alto(self):
        resultado = descuento(50000, False, False)
        print(resultado)
