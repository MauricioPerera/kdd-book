"""Oraculo congelado: el valor del color y del espaciado no cambian.
"""

import os
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))


def texto(ruta):
    with open(os.path.join(AQUI, ruta), encoding='utf-8') as fh:
        return fh.read()



class TemaTest(unittest.TestCase):

    def test_los_valores_no_cambian(self):
        contenido = texto('proyecto/app.css')
        self.assertIn('oklch(0.6 0.2 30)', contenido)
        self.assertIn('--spacing-card: 1.5rem', contenido)


if __name__ == '__main__':
    unittest.main()
