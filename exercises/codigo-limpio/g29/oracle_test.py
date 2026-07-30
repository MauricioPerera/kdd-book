"""Oraculo congelado G29.

Refactor puro: pasa igual con las condiciones en negativo y en positivo,
asi que no puede decir si la tecnica se aplico. Eso lo decide el instrumento.
"""

import unittest

from target import puede_inscribirse


class PuedeInscribirseTest(unittest.TestCase):

    def test_con_cupos_y_sin_bloqueo(self):
        self.assertIs(puede_inscribirse(5, False), True)

    def test_bloqueado_nunca_puede(self):
        self.assertIs(puede_inscribirse(5, True), False)

    def test_sin_cupos_no_puede(self):
        self.assertIs(puede_inscribirse(0, False), False)

    def test_bloqueado_y_sin_cupos(self):
        self.assertIs(puede_inscribirse(0, True), False)

    def test_cupos_negativos_no_habilitan(self):
        self.assertIs(puede_inscribirse(-3, False), False)


if __name__ == '__main__':
    unittest.main()
