"""Oraculo congelado G9.

Refactor puro: borrar una funcion que nadie llama no cambia nada. El
oraculo nunca la nombro, y por eso puede pasar antes y despues.
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

    def test_sin_inscriptos(self):
        self.assertEqual(cupos_libres(40, 0), 40)

    def test_capacidad_cero(self):
        self.assertEqual(cupos_libres(0, 5), 0)


if __name__ == '__main__':
    unittest.main()
