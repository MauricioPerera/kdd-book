"""Oraculo congelado: el aviso sigue diciendo lo mismo.
"""

import os
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))


def texto(ruta):
    with open(os.path.join(AQUI, ruta), encoding='utf-8') as fh:
        return fh.read()



class AvisoTest(unittest.TestCase):

    def test_el_aviso_no_cambia(self):
        contenido = texto('proyecto/index.html')
        self.assertIn('Aviso obligatorio', contenido)
        self.assertIn('text-sm', contenido)


if __name__ == '__main__':
    unittest.main()
