"""Oraculo congelado del ejercicio ISP.

Refactor puro: angostar la dependencia declarada no cambia lo que el buscador
devuelve, porque el repositorio real sigue sirviendo. El oraculo pasa igual
antes y despues.
"""

import unittest

from cliente import Buscador
from repositorio import RepositorioLibros


class BuscadorTest(unittest.TestCase):

    def test_devuelve_lo_encontrado(self):
        self.assertEqual(Buscador().por_titulo(RepositorioLibros(), 'KDD'),
                         {'titulo': 'KDD'})

    def test_acepta_cualquier_titulo(self):
        self.assertEqual(Buscador().por_titulo(RepositorioLibros(), 'otro'),
                         {'titulo': 'otro'})

    def test_titulo_vacio(self):
        self.assertEqual(Buscador().por_titulo(RepositorioLibros(), ''),
                         {'titulo': ''})

    def test_sirve_cualquier_objeto_con_buscar(self):
        class Minimo:
            def buscar(self, titulo):
                return {'titulo': titulo.upper()}
        self.assertEqual(Buscador().por_titulo(Minimo(), 'kdd'), {'titulo': 'KDD'})

    def test_no_toca_el_repositorio(self):
        repo = RepositorioLibros()
        Buscador().por_titulo(repo, 'KDD')
        self.assertEqual(repo.exportar(), [])
