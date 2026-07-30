"""Oraculo congelado C5.

Refactor puro: borrar codigo comentado no cambia nada, porque el codigo
comentado no se ejecuta. El oraculo pasa igual antes y despues.
"""

import unittest

from target import total_con_iva


class TotalConIvaTest(unittest.TestCase):

    def test_caso_simple(self):
        self.assertEqual(total_con_iva(100), 121.0)

    def test_redondea_a_dos_decimales(self):
        self.assertEqual(total_con_iva(99.99), 120.99)

    def test_neto_cero(self):
        self.assertEqual(total_con_iva(0), 0.0)

    def test_neto_negativo(self):
        self.assertEqual(total_con_iva(-100), -121.0)

    def test_devuelve_float(self):
        self.assertIsInstance(total_con_iva(10), float)


if __name__ == '__main__':
    unittest.main()
