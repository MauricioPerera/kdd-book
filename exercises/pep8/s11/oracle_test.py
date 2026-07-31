"""Oraculo congelado: lo que el modulo serializa y su version no cambian.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import target  # noqa: E402


class ComportamientoTest(unittest.TestCase):

    def test_lo_observable_no_cambia(self):
        self.assertEqual(target.serializar({"b": 1, "a": 2}), '{"a": 2, "b": 1}')
        self.assertEqual(target.__version__, '1.4.0')


if __name__ == '__main__':
    unittest.main()
