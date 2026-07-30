"""Pruebas adicionales del proyecto: los caminos que el oraculo no recorre."""

import unittest

from cupos import estado


class CoberturaTest(unittest.TestCase):

    def test_sin_capacidad(self):
        self.assertEqual(estado(0, 0, True), 'sin capacidad')

    def test_capacidad_negativa(self):
        self.assertEqual(estado(-5, 0, True), 'sin capacidad')

    def test_sobrevendido(self):
        self.assertEqual(estado(10, 11, True), 'sobrevendido')

    def test_completo(self):
        self.assertEqual(estado(10, 10, True), 'completo')
