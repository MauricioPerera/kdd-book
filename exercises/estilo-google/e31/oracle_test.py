"""Oraculo congelado: el comportamiento descrito no cambia.
"""

import os
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))


def texto():
    with open(os.path.join(AQUI, 'target.md'), encoding='utf-8') as fh:
        return fh.read()



class ComportamientoTest(unittest.TestCase):

    def test_el_comportamiento_descrito_no_cambia(self):
        self.assertIn('server', texto())
        self.assertIn('error', texto())


if __name__ == '__main__':
    unittest.main()
