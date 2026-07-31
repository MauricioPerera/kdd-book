"""Oraculo congelado: la explicacion no cambia.
"""

import os
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))


def texto():
    with open(os.path.join(AQUI, 'target.md'), encoding='utf-8') as fh:
        return fh.read()



class NotaTest(unittest.TestCase):

    def test_la_explicacion_no_cambia(self):
        self.assertIn('cache was not cleared', texto().lower())


if __name__ == '__main__':
    unittest.main()
