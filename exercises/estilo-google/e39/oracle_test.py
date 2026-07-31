"""Oraculo congelado: la oracion no cambia.
"""

import os
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))


def texto():
    with open(os.path.join(AQUI, 'target.md'), encoding='utf-8') as fh:
        return fh.read()



class OracionTest(unittest.TestCase):

    def test_la_oracion_no_cambia(self):
        self.assertIn('unexpected', texto())
        self.assertIn('surprised everyone', texto())


if __name__ == '__main__':
    unittest.main()
