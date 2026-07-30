"""Oraculo congelado 142.

Refactor puro: partir la expresion en valores intermedios no cambia lo
que decide. El oraculo pasa igual antes y despues, y por eso no puede
decir si la tecnica se aplico.
"""

import unittest

from target import admite_inscripcion


class AdmiteInscripcionTest(unittest.TestCase):

    def test_caso_favorable(self):
        self.assertIs(admite_inscripcion(5, True, True, False), True)

    def test_sin_cupos(self):
        self.assertIs(admite_inscripcion(0, True, True, False), False)

    def test_cerrado(self):
        self.assertIs(admite_inscripcion(5, False, True, False), False)

    def test_bloqueado_pero_pagado(self):
        self.assertIs(admite_inscripcion(5, True, True, True), True)

    def test_bloqueado_y_sin_pagar(self):
        self.assertIs(admite_inscripcion(5, True, False, True), False)

    def test_sin_pagar_pero_no_bloqueado(self):
        self.assertIs(admite_inscripcion(5, True, False, False), True)


if __name__ == '__main__':
    unittest.main()
