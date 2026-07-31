"""Oraculo congelado: el calculo de cupos no cambia.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import target  # noqa: E402


class ComportamientoTest(unittest.TestCase):

    def test_lo_observable_no_cambia(self):
        self.assertEqual(target.libres(4), 6)


if __name__ == '__main__':
    unittest.main()
