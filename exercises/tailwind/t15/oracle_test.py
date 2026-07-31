"""Oraculo congelado: el titulo sigue diciendo lo mismo.
"""

import os
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))


def texto(ruta):
    with open(os.path.join(AQUI, ruta), encoding='utf-8') as fh:
        return fh.read()



class TituloTest(unittest.TestCase):

    def test_el_titulo_no_cambia(self):
        self.assertIn('Bienvenido', texto('proyecto/index.html'))


if __name__ == '__main__':
    unittest.main()
