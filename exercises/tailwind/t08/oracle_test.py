"""Oraculo congelado: el boton sigue diciendo lo mismo y con el mismo relleno.
"""

import os
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))


def texto(ruta):
    with open(os.path.join(AQUI, ruta), encoding='utf-8') as fh:
        return fh.read()



class BotonTest(unittest.TestCase):

    def test_el_boton_no_cambia(self):
        contenido = texto('proyecto/index.html')
        self.assertIn('Enviar', contenido)
        self.assertIn('px-4', contenido)
        self.assertIn('py-2', contenido)


if __name__ == '__main__':
    unittest.main()
