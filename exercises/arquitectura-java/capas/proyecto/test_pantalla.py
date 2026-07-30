"""Oraculo congelado del ejercicio de capas.

Refactor puro: pasar por el servicio en vez de ir directo al DAO no cambia lo
que la pantalla muestra. El oraculo pasa igual antes y despues, asi que quien
dice si la tecnica se aplico es el instrumento.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vistas.pantalla import pantalla_de_libros  # noqa: E402


class PantallaTest(unittest.TestCase):

    def test_muestra_los_titulos(self):
        self.assertEqual(pantalla_de_libros(), 'Contratos | KDD')

    def test_estan_ordenados(self):
        partes = pantalla_de_libros().split(' | ')
        self.assertEqual(partes, sorted(partes))

    def test_devuelve_texto(self):
        self.assertIsInstance(pantalla_de_libros(), str)

    def test_incluye_todos(self):
        self.assertEqual(len(pantalla_de_libros().split(' | ')), 2)

    def test_es_estable(self):
        self.assertEqual(pantalla_de_libros(), pantalla_de_libros())
