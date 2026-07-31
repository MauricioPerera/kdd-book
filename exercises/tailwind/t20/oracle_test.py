"""Oraculo congelado: la tarjeta sigue mostrando el mismo texto.
"""

import os
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))


def texto(ruta):
    with open(os.path.join(AQUI, ruta), encoding='utf-8') as fh:
        return fh.read()



class TarjetaTest(unittest.TestCase):

    def test_la_tarjeta_no_cambia(self):
        contenido = texto('proyecto/Card.jsx')
        self.assertIn('Tarjeta', contenido)
        self.assertIn('function Card', contenido)


if __name__ == '__main__':
    unittest.main()
