"""Oraculo congelado G5.

Refactor puro: unificar dos copias del mismo calculo no cambia el
resultado. El oraculo pasa igual antes y despues.
"""

import unittest

from target import total_evento, total_taller


class TotalesTest(unittest.TestCase):

    def test_evento_simple(self):
        self.assertEqual(total_evento(100, 2), 242.0)

    def test_taller_simple(self):
        self.assertEqual(total_taller(100, 2), 242.0)

    def test_ambos_coinciden(self):
        self.assertEqual(total_evento(37.5, 3), total_taller(37.5, 3))

    def test_cantidad_cero(self):
        self.assertEqual(total_evento(100, 0), 0.0)

    def test_redondea_a_dos_decimales(self):
        self.assertEqual(total_evento(33.33, 1), 40.33)


if __name__ == '__main__':
    unittest.main()
