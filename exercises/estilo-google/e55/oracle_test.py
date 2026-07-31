"""Oraculo congelado: la formula no cambia.
"""

import os
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))


def texto():
    with open(os.path.join(AQUI, 'target.md'), encoding='utf-8') as fh:
        return fh.read()



class AreaTest(unittest.TestCase):

    def test_la_formula_no_cambia(self):
        self.assertIn('area is', texto())
        self.assertIn('a \\times b', texto())


if __name__ == '__main__':
    unittest.main()
