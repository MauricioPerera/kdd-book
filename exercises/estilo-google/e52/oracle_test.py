"""Oraculo congelado: la seccion de opciones sigue estando.
"""

import os
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))


def texto():
    with open(os.path.join(AQUI, 'target.md'), encoding='utf-8') as fh:
        return fh.read()



class EstructuraTest(unittest.TestCase):

    def test_la_seccion_de_opciones_sigue_estando(self):
        self.assertIn('Options', texto())


if __name__ == '__main__':
    unittest.main()
