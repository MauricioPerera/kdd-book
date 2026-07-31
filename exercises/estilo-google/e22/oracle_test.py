"""Oraculo congelado: la instruccion sigue senalando el mismo archivo.
"""

import os
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))


def texto():
    with open(os.path.join(AQUI, 'target.md'), encoding='utf-8') as fh:
        return fh.read()



class InstruccionTest(unittest.TestCase):

    def test_la_instruccion_no_cambia(self):
        self.assertTrue(texto().startswith('Use a config file'))
        self.assertIn('config.yaml', texto())


if __name__ == '__main__':
    unittest.main()
