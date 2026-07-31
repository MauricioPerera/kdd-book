"""Oraculo congelado: la paleta tiene los mismos colores.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import target  # noqa: E402


class ComportamientoTest(unittest.TestCase):

    def test_lo_observable_no_cambia(self):
        self.assertEqual(target.COLORES, ["rojo", "verde", "amarillo"])
        self.assertEqual(target.cuantos(), 3)


if __name__ == '__main__':
    unittest.main()
