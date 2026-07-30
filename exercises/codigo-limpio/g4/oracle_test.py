"""Oraculo congelado G4.

Refactor puro: quitar supresiones y el import que una de ellas tapaba no
cambia el resultado. El oraculo pasa igual antes y despues.
"""

import unittest

from target import cupos_libres


class CuposLibresTest(unittest.TestCase):

    def test_quedan_cupos(self):
        self.assertEqual(cupos_libres(40, 12), 28)

    def test_respeta_el_tope(self):
        self.assertEqual(cupos_libres(500, 0), 100)

    def test_sobrevendido_no_da_negativo(self):
        self.assertEqual(cupos_libres(40, 55), 0)

    def test_capacidad_cero(self):
        self.assertEqual(cupos_libres(0, 0), 0)

    def test_justo_en_el_tope(self):
        self.assertEqual(cupos_libres(100, 100), 0)


if __name__ == '__main__':
    unittest.main()
