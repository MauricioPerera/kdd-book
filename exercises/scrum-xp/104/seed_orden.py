"""Pruebas del carrito que dependen del orden.

`test_hay_dos` solo pasa si `test_carga` corrio antes y dejo el carrito
cargado. Corridas juntas y en orden alfabetico funciona; sola, falla.
"""

import unittest

import carrito


class OrdenTest(unittest.TestCase):

    def test_carga(self):
        carrito.agregar('uno')
        carrito.agregar('dos')
        self.assertEqual(carrito.total(), 2)

    def test_hay_dos(self):
        self.assertEqual(carrito.total(), 2)
