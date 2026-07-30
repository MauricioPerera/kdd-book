"""Oraculo congelado del ejercicio COC.

Escrito contra los nombres de destino: seguir la convencion cambia como se
lee el objeto, asi que el seed arranca en rojo. El instrumento sigue haciendo
falta, porque el oraculo no sabe cuales son las columnas de la tabla.
"""

import unittest

from modelo import Libro


class LibroTest(unittest.TestCase):

    def test_guarda_el_titulo(self):
        self.assertEqual(Libro('KDD', 'Perera', 2026).titulo, 'KDD')

    def test_guarda_el_autor(self):
        self.assertEqual(Libro('KDD', 'Perera', 2026).autor, 'Perera')

    def test_guarda_el_anio(self):
        self.assertEqual(Libro('KDD', 'Perera', 2026).anio, 2026)

    def test_acepta_posicionales(self):
        libro = Libro('A', 'B', 1)
        self.assertEqual((libro.titulo, libro.autor, libro.anio), ('A', 'B', 1))

    def test_no_agrega_campos(self):
        campos = sorted(vars(Libro('A', 'B', 1)))
        self.assertEqual(campos, ['anio', 'autor', 'titulo'])
