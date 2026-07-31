"""Oraculo congelado: el color que usa el body sigue siendo el mismo.
"""

import os
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))


def texto(ruta):
    with open(os.path.join(AQUI, ruta), encoding='utf-8') as fh:
        return fh.read()



class ColorTest(unittest.TestCase):

    def test_el_color_no_cambia(self):
        contenido = texto('proyecto/app.css')
        self.assertIn('oklch(0.7 0.15 250)', contenido)
        self.assertIn('var(--color-brand)', contenido)


if __name__ == '__main__':
    unittest.main()
