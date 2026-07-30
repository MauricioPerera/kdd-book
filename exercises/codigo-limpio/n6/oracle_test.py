"""Oraculo congelado N6.

Refactor puro: renombrar variables locales y parametros posicionales no
cambia nada observable. El oraculo pasa igual antes y despues.
"""

import unittest

from target import resumen_inscripcion


class ResumenInscripcionTest(unittest.TestCase):

    def test_arma_el_resumen(self):
        self.assertEqual(resumen_inscripcion('KDD', 3), 'KDD: 6')

    def test_cero_cupos(self):
        self.assertEqual(resumen_inscripcion('KDD', 0), 'KDD: 0')

    def test_nombre_vacio(self):
        self.assertEqual(resumen_inscripcion('', 1), ': 2')

    def test_cupos_negativos(self):
        self.assertEqual(resumen_inscripcion('KDD', -2), 'KDD: -4')

    def test_no_recorta_el_nombre(self):
        self.assertEqual(resumen_inscripcion(' KDD ', 1), ' KDD : 2')


if __name__ == '__main__':
    unittest.main()
