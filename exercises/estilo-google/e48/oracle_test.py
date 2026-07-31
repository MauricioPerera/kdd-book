"""Oraculo congelado: la fecha no cambia.
"""

import os
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))


def texto():
    with open(os.path.join(AQUI, 'target.md'), encoding='utf-8') as fh:
        return fh.read()



class FechaTest(unittest.TestCase):

    def test_la_fecha_no_cambia(self):
        self.assertIn('July', texto())
        self.assertIn('ships', texto())


if __name__ == '__main__':
    unittest.main()
