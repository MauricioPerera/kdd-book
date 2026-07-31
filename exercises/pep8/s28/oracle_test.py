"""Oraculo congelado: la cuenta gira igual, con el nombre de destino.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import target  # noqa: E402


class ComportamientoTest(unittest.TestCase):

    def test_lo_observable_no_cambia(self):
        self.assertEqual(target.CuentaCorriente(100).girar(30), 70)


if __name__ == '__main__':
    unittest.main()
