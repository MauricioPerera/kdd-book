"""Oraculo congelado T1: fija el comportamiento, no la cobertura.

Cubre solo dos de los cinco caminos a proposito. Subir la cobertura es tarea
del archivo de pruebas que si se puede tocar; este esta sellado.
"""

import unittest

from cupos import estado


class EstadoTest(unittest.TestCase):

    def test_disponible(self):
        self.assertEqual(estado(10, 1, True), 'disponible')

    def test_inactivo(self):
        self.assertEqual(estado(10, 1, False), 'inactivo')
