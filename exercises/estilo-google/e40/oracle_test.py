"""Oraculo congelado: la frase no cambia.
"""

import os
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))


def texto():
    with open(os.path.join(AQUI, 'target.md'), encoding='utf-8') as fh:
        return fh.read()



class ListaTest(unittest.TestCase):

    def test_la_frase_no_cambia(self):
        self.assertTrue(texto().startswith('The list continues'))


if __name__ == '__main__':
    unittest.main()
