"""Oraculo congelado: el dato no cambia.
"""

import os
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))


def texto():
    with open(os.path.join(AQUI, 'target.md'), encoding='utf-8') as fh:
        return fh.read()



class ValorTest(unittest.TestCase):

    def test_el_dato_no_cambia(self):
        self.assertIn('seconds', texto())
        self.assertIn('approximately', texto())
        self.assertIn('varies', texto())


if __name__ == '__main__':
    unittest.main()
