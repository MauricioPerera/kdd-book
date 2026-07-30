"""Oraculo congelado G25.

Refactor puro: los numeros valen lo mismo tengan nombre o no. El oraculo
pasa en los dos casos y no puede decir si la tecnica se aplico.
"""

import unittest

from target import precio_con_recargo


class PrecioConRecargoTest(unittest.TestCase):

    def test_recargo_tardio(self):
        self.assertEqual(precio_con_recargo(100, 3), 135.0)

    def test_recargo_normal(self):
        self.assertEqual(precio_con_recargo(100, 60), 110.0)

    def test_el_limite_no_lleva_recargo_tardio(self):
        self.assertEqual(precio_con_recargo(100, 15), 110.0)

    def test_justo_debajo_del_limite(self):
        self.assertEqual(precio_con_recargo(100, 14), 135.0)

    def test_redondea_a_dos_decimales(self):
        self.assertEqual(precio_con_recargo(99.99, 60), 109.99)


if __name__ == '__main__':
    unittest.main()
