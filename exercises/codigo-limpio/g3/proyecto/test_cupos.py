"""Oraculo congelado del ejercicio de limites.

Fija el comportamiento en los casos comodos, lejos de los bordes, y esta
sellado. Justamente por eso no alcanza: una suite puede pasar entera y seguir
sin enterarse de que un limite se corrio un lugar. Eso lo dice el instrumento,
mutando el codigo y viendo si alguien protesta.
"""

import unittest

from cupos import estado_cupos


class EstadoCuposTest(unittest.TestCase):

    def test_hay_lugar_de_sobra(self):
        self.assertEqual(estado_cupos(10, 3), 'disponible')

    def test_muy_sobrevendido(self):
        self.assertEqual(estado_cupos(10, 20), 'sobrevendido')
