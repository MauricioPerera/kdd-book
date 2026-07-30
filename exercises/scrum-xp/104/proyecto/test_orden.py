"""Pruebas del carrito, cada una parada sola."""

import unittest

import carrito


class OrdenTest(unittest.TestCase):

    def setUp(self):
        carrito.ITEMS.clear()

    def test_carga(self):
        carrito.agregar('uno')
        carrito.agregar('dos')
        self.assertEqual(carrito.total(), 2)

    def test_hay_dos(self):
        carrito.agregar('uno')
        carrito.agregar('dos')
        self.assertEqual(carrito.total(), 2)
