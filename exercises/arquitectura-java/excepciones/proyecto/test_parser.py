"""Oraculo congelado del ejercicio de excepciones.

Refactor puro para las entradas que fija: con textos, `except:` y
`except ValueError:` atrapan lo mismo. El oraculo pasa igual antes y despues.
"""

import unittest

from parser_datos import leer_cupos, leer_precio


class LeerCuposTest(unittest.TestCase):

    def test_numero_valido(self):
        self.assertEqual(leer_cupos('40'), 40)

    def test_texto_invalido(self):
        self.assertEqual(leer_cupos('muchos'), 0)

    def test_vacio(self):
        self.assertEqual(leer_cupos(''), 0)


class LeerPrecioTest(unittest.TestCase):

    def test_decimal_valido(self):
        self.assertEqual(leer_precio('12.5'), 12.5)

    def test_texto_invalido(self):
        self.assertEqual(leer_precio('gratis'), 0.0)

    def test_entero_como_texto(self):
        self.assertEqual(leer_precio('7'), 7.0)
