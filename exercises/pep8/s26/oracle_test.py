"""Oraculo congelado: el promedio no cambia.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import target  # noqa: E402


class ComportamientoTest(unittest.TestCase):

    def test_lo_observable_no_cambia(self):
        self.assertEqual(target.promedio([2, 4, 0, 6]), 4.0)


if __name__ == '__main__':
    unittest.main()
