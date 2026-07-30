"""Oraculo congelado 104: la funcionalidad del carrito.

No sabe nada de aislamiento. Su trabajo es decir que `agregar` y `total`
siguen haciendo lo mismo; si las pruebas dependen unas de otras lo dice el
instrumento.
"""

import unittest

import carrito


class CarritoTest(unittest.TestCase):

    def setUp(self):
        carrito.ITEMS.clear()

    def test_agregar_devuelve_la_cantidad(self):
        self.assertEqual(carrito.agregar('a'), 1)

    def test_total_cuenta_lo_agregado(self):
        carrito.agregar('a')
        carrito.agregar('b')
        self.assertEqual(carrito.total(), 2)

    def test_arranca_vacio(self):
        self.assertEqual(carrito.total(), 0)
