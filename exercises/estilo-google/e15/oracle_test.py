"""Oraculo congelado: la instruccion sigue pidiendo lo mismo.
"""

import os
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))


def texto():
    with open(os.path.join(AQUI, 'target.md'), encoding='utf-8') as fh:
        return fh.read()



class FraseTest(unittest.TestCase):

    def test_la_instruccion_no_cambia(self):
        self.assertTrue(texto().startswith('Add the domain to the'))


if __name__ == '__main__':
    unittest.main()
