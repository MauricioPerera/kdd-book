"""Oraculo congelado: la cuenta da lo mismo.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import target  # noqa: E402


class ComportamientoTest(unittest.TestCase):

    def test_lo_observable_no_cambia(self):
        self.assertEqual(target.total(100, 20, 5), 115)


if __name__ == '__main__':
    unittest.main()
