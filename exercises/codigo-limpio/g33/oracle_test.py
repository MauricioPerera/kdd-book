"""Oraculo congelado G33.

Refactor puro: nombrar la expresion de limite no cambia su valor. El
oraculo pasa igual antes y despues.
"""

import unittest

from target import rango_de_nivel


class RangoDeNivelTest(unittest.TestCase):

    def test_nivel_uno(self):
        self.assertEqual(rango_de_nivel(1), (2, 20, '2'))

    def test_nivel_cero(self):
        self.assertEqual(rango_de_nivel(0), (1, 10, '1'))

    def test_nivel_negativo(self):
        self.assertEqual(rango_de_nivel(-3), (-2, -20, '-2'))

    def test_devuelve_una_tupla_de_tres(self):
        self.assertEqual(len(rango_de_nivel(5)), 3)

    def test_la_etiqueta_es_texto(self):
        self.assertIsInstance(rango_de_nivel(5)[2], str)


if __name__ == '__main__':
    unittest.main()
