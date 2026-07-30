"""Oraculo congelado G12.

Refactor puro: borrar un import que nadie usa y una variable que nadie lee
no cambia nada observable. El oraculo pasa igual antes y despues.
"""

import unittest

from target import cupos_libres


class CuposLibresTest(unittest.TestCase):

    def test_quedan_cupos(self):
        self.assertEqual(cupos_libres(40, 12), 28)

    def test_exactamente_lleno(self):
        self.assertEqual(cupos_libres(40, 40), 0)

    def test_sobrevendido_no_da_negativo(self):
        self.assertEqual(cupos_libres(40, 55), 0)

    def test_capacidad_cero(self):
        self.assertEqual(cupos_libres(0, 0), 0)

    def test_sin_inscriptos(self):
        self.assertEqual(cupos_libres(40, 0), 40)


if __name__ == '__main__':
    unittest.main()
