"""Oraculo congelado: el carrito suma lo mismo.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import target  # noqa: E402


class ComportamientoTest(unittest.TestCase):

    def test_lo_observable_no_cambia(self):
        self.assertEqual(target.Carrito([1, 2, 3]).total(), 6)


if __name__ == '__main__':
    unittest.main()
