"""Oraculo congelado N5.

Refactor puro: renombrar variables locales no cambia nada observable. El
oraculo pasa igual antes y despues.
"""

import unittest

from target import resumen_de_cupos


def _evento(capacidad, inscriptos, activo=True):
    return {'capacidad': capacidad, 'inscriptos': inscriptos, 'activo': activo}


class ResumenDeCuposTest(unittest.TestCase):

    def test_suma_los_activos(self):
        self.assertEqual(resumen_de_cupos([_evento(10, 3), _evento(5, 1)]), 11)

    def test_ignora_los_inactivos(self):
        self.assertEqual(
            resumen_de_cupos([_evento(10, 3), _evento(5, 1, activo=False)]), 7)

    def test_lista_vacia(self):
        self.assertEqual(resumen_de_cupos([]), 0)

    def test_sobrevendido_no_da_negativo(self):
        self.assertEqual(resumen_de_cupos([_evento(5, 20)]), 0)

    def test_todo_lleno(self):
        self.assertEqual(resumen_de_cupos([_evento(10, 10)]), 0)


if __name__ == '__main__':
    unittest.main()
