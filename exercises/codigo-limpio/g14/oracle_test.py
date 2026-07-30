"""Oraculo congelado G14.

Refactor puro: mover la cuenta a la clase que tiene los datos no cambia el
resultado. El oraculo pasa igual antes y despues.
"""

import unittest

from target import Empleado, liquidar


class LiquidarTest(unittest.TestCase):

    def test_pago_simple(self):
        self.assertEqual(liquidar(Empleado(10, 8, 0)), 80)

    def test_con_extra(self):
        self.assertEqual(liquidar(Empleado(10, 8, 25)), 105)

    def test_sin_horas(self):
        self.assertEqual(liquidar(Empleado(10, 0, 25)), 25)

    def test_tarifa_decimal(self):
        self.assertEqual(liquidar(Empleado(12.5, 4, 0)), 50.0)

    def test_extra_negativo_descuenta(self):
        self.assertEqual(liquidar(Empleado(10, 8, -30)), 50)


if __name__ == '__main__':
    unittest.main()
