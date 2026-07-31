"""Oraculo congelado: la funcionalidad sigue en el mismo estado.
"""

import os
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))


def texto():
    with open(os.path.join(AQUI, 'target.md'), encoding='utf-8') as fh:
        return fh.read()



class EstadoTest(unittest.TestCase):

    def test_el_estado_de_la_funcionalidad_no_cambia(self):
        self.assertTrue(texto().startswith('This feature is'))
        self.assertIn('beta', texto())


if __name__ == '__main__':
    unittest.main()
