"""Oraculo congelado: el calculo del IVA no cambia.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import target  # noqa: E402


class ComportamientoTest(unittest.TestCase):

    def test_lo_observable_no_cambia(self):
        self.assertAlmostEqual(target.con_iva(100), 121.0)


if __name__ == '__main__':
    unittest.main()
