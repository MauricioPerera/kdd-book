"""Oraculo congelado 143.

Refactor puro: partir un metodo largo en varios cortos no cambia lo que
devuelve. El oraculo pasa igual antes y despues.
"""

import unittest

from target import informe_de_evento


def _evento(nombre="KDD", ciudad="Rosario", capacidad=10, inscriptos=3):
    return {'nombre': nombre, 'ciudad': ciudad,
            'capacidad': capacidad, 'inscriptos': inscriptos}


class InformeDeEventoTest(unittest.TestCase):

    def test_disponible(self):
        self.assertEqual(informe_de_evento(_evento()),
                         'KDD (Rosario) - disponible - 7 cupos')

    def test_completo(self):
        self.assertEqual(informe_de_evento(_evento(inscriptos=10)),
                         'KDD (Rosario) - completo - 0 cupos')

    def test_sobrevendido_no_da_negativo(self):
        self.assertEqual(informe_de_evento(_evento(inscriptos=25)),
                         'KDD (Rosario) - completo - 0 cupos')

    def test_recorta_los_espacios(self):
        self.assertEqual(informe_de_evento(_evento(nombre='  KDD ', ciudad=' Lima ')),
                         'KDD (Lima) - disponible - 7 cupos')

    def test_capacidad_cero(self):
        self.assertEqual(informe_de_evento(_evento(capacidad=0, inscriptos=0)),
                         'KDD (Rosario) - completo - 0 cupos')


if __name__ == '__main__':
    unittest.main()
