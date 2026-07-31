"""Oraculo congelado: la instruccion sigue fijando el mismo modo.
"""

import os
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))


def texto():
    with open(os.path.join(AQUI, 'target.md'), encoding='utf-8') as fh:
        return fh.read()



class InstruccionTest(unittest.TestCase):

    def test_la_instruccion_no_cambia(self):
        self.assertIn('auto', texto())
        self.assertTrue(texto().startswith('Set the mode to'))


if __name__ == '__main__':
    unittest.main()
