"""Oraculo congelado G10.

Refactor puro: mover una declaracion junto a su uso no cambia el resultado,
porque el calculo no tiene efectos. El oraculo pasa igual antes y despues.
"""

import unittest

from target import resumen_evento


class ResumenEventoTest(unittest.TestCase):

    def test_inactivo(self):
        self.assertEqual(resumen_evento('kdd', 10, 1, False), 'inactivo')

    def test_sin_capacidad(self):
        self.assertEqual(resumen_evento('kdd', 0, 0, True), 'sin capacidad')

    def test_sobrevendido(self):
        self.assertEqual(resumen_evento('kdd', 10, 11, True), 'sobrevendido')

    def test_completo(self):
        self.assertEqual(resumen_evento('kdd', 10, 10, True), 'completo')

    def test_disponible_devuelve_la_etiqueta(self):
        self.assertEqual(resumen_evento('  kdd ', 10, 1, True), 'KDD')

    def test_el_orden_de_las_guardas_manda(self):
        self.assertEqual(resumen_evento('kdd', 0, 5, False), 'inactivo')


if __name__ == '__main__':
    unittest.main()
