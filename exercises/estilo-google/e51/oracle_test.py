"""Oraculo congelado: la afirmacion sobre la API no cambia.
"""

import os
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))


def texto():
    with open(os.path.join(AQUI, 'target.md'), encoding='utf-8') as fh:
        return fh.read()



class ApiTest(unittest.TestCase):

    def test_la_afirmacion_no_cambia(self):
        self.assertIn('API is stable', texto())


if __name__ == '__main__':
    unittest.main()
