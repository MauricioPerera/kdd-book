"""Oraculo congelado del ejercicio AOP.

Refactor puro: registrar no cambia lo que la funcion devuelve, y por eso el
oraculo pasa igual con y sin el logging. Que lo transversal salga del negocio
lo dice el instrumento.
"""

import unittest

from negocio.inscripciones import total_inscripcion


class TotalInscripcionTest(unittest.TestCase):

    def test_caso_simple(self):
        self.assertEqual(total_inscripcion(100, 3), 300)

    def test_cantidad_cero(self):
        self.assertEqual(total_inscripcion(100, 0), 0)

    def test_base_decimal(self):
        self.assertEqual(total_inscripcion(12.5, 4), 50.0)

    def test_cantidad_uno(self):
        self.assertEqual(total_inscripcion(99, 1), 99)

    def test_no_redondea(self):
        self.assertEqual(total_inscripcion(0.1, 3), 0.1 * 3)
