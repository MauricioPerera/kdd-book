"""Oraculo congelado J2.

Refactor puro: dejar de heredar y citar las constantes por su nombre no
cambia que valen. El oraculo pasa igual antes y despues.
"""

import unittest

from target import ServicioEventos


class ServicioEventosTest(unittest.TestCase):

    def test_cantidad_en_rango(self):
        self.assertIs(ServicioEventos().cupos_validos(40), True)

    def test_justo_en_el_minimo(self):
        self.assertIs(ServicioEventos().cupos_validos(5), True)

    def test_justo_en_el_tope(self):
        self.assertIs(ServicioEventos().cupos_validos(100), True)

    def test_debajo_del_minimo(self):
        self.assertIs(ServicioEventos().cupos_validos(4), False)

    def test_arriba_del_tope(self):
        self.assertIs(ServicioEventos().cupos_validos(101), False)


if __name__ == '__main__':
    unittest.main()
