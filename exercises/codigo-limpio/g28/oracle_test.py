"""Oraculo congelado G28.

Refactor puro: extraer la condicion a una funcion con nombre no cambia
que decide. El oraculo pasa igual antes y despues.
"""

import unittest

from target import estado_inscripcion


class EstadoInscripcionTest(unittest.TestCase):

    def test_todo_en_orden(self):
        self.assertEqual(estado_inscripcion(True, True, False, 5), 'confirmada')

    def test_sin_pagar(self):
        self.assertEqual(estado_inscripcion(True, False, False, 5), 'pendiente')

    def test_vencido(self):
        self.assertEqual(estado_inscripcion(True, True, True, 5), 'pendiente')

    def test_sin_cupos(self):
        self.assertEqual(estado_inscripcion(True, True, False, 0), 'pendiente')

    def test_no_inscripto(self):
        self.assertEqual(estado_inscripcion(False, True, False, 5), 'pendiente')

    def test_cupos_negativos(self):
        self.assertEqual(estado_inscripcion(True, True, False, -1), 'pendiente')


if __name__ == '__main__':
    unittest.main()
