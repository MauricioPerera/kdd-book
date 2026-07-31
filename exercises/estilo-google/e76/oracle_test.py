"""Oraculo congelado: el parrafo sigue empezando igual.
"""

import os
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))


def texto():
    with open(os.path.join(AQUI, 'target.md'), encoding='utf-8') as fh:
        return fh.read()



class ParrafoTest(unittest.TestCase):

    def test_el_parrafo_sigue_empezando_igual(self):
        self.assertTrue(texto().startswith('Some text'))


if __name__ == '__main__':
    unittest.main()
