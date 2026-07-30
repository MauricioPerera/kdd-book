"""Oraculo congelado F3.

Un argumento de indicador no se quita sin partir la funcion en dos, asi que
el oraculo nombra las dos y el seed arranca en rojo.
"""

import unittest

from target import formatear_titulo, formatear_titulo_destacado


class FormatearTituloTest(unittest.TestCase):

    def test_recorta_espacios(self):
        self.assertEqual(formatear_titulo('  KDD  '), 'KDD')

    def test_no_cambia_las_mayusculas(self):
        self.assertEqual(formatear_titulo('Kdd En La Practica'), 'Kdd En La Practica')

    def test_destacado_recorta_y_sube(self):
        self.assertEqual(formatear_titulo_destacado('  kdd  '), 'KDD')

    def test_destacado_sobre_texto_ya_en_mayusculas(self):
        self.assertEqual(formatear_titulo_destacado('KDD'), 'KDD')

    def test_solo_espacios(self):
        self.assertEqual(formatear_titulo('   '), '')
        self.assertEqual(formatear_titulo_destacado('   '), '')


if __name__ == '__main__':
    unittest.main()
