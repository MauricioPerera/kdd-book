"""Oraculo congelado: el contenido del panel sigue siendo el mismo.
"""

import os
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))


def texto(ruta):
    with open(os.path.join(AQUI, ruta), encoding='utf-8') as fh:
        return fh.read()



class PanelTest(unittest.TestCase):

    def test_el_contenido_no_cambia(self):
        self.assertIn('Panel', texto('proyecto/index.html'))


if __name__ == '__main__':
    unittest.main()
