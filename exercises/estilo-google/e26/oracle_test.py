"""Oraculo congelado: el encabezado sigue hablando de lo mismo.
"""

import os
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))


def texto():
    with open(os.path.join(AQUI, 'target.md'), encoding='utf-8') as fh:
        return fh.read()



class EncabezadoTest(unittest.TestCase):

    def test_el_tema_del_encabezado_no_cambia(self):
        self.assertIn('development environment', texto().lower())


if __name__ == '__main__':
    unittest.main()
