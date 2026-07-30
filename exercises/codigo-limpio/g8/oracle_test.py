"""Oraculo congelado G8.

Refactor puro: achicar la superficie publica no cambia lo que la clase
calcula. El oraculo usa solo `total`, que es lo unico que era de afuera.
"""

import unittest

from target import Inscripcion


class InscripcionTest(unittest.TestCase):

    def test_total_simple(self):
        self.assertEqual(Inscripcion(100, 2).total(), 242.0)

    def test_cantidad_cero(self):
        self.assertEqual(Inscripcion(100, 0).total(), 0.0)

    def test_redondea_a_dos_decimales(self):
        self.assertEqual(Inscripcion(33.33, 1).total(), 40.33)

    def test_precio_decimal(self):
        self.assertEqual(Inscripcion(10.5, 4).total(), 50.82)

    def test_guarda_lo_que_recibe(self):
        i = Inscripcion(7, 3)
        self.assertEqual((i.precio, i.cantidad), (7, 3))


if __name__ == '__main__':
    unittest.main()
