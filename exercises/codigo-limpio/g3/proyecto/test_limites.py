"""Pruebas de borde del evento: los casos justo en el limite."""

import unittest

from cupos import estado_cupos


class LimitesTest(unittest.TestCase):

    def test_justo_completo(self):
        self.assertEqual(estado_cupos(10, 10), 'completo')

    def test_uno_antes_del_limite(self):
        self.assertEqual(estado_cupos(10, 9), 'disponible')

    def test_uno_despues_del_limite(self):
        self.assertEqual(estado_cupos(10, 11), 'sobrevendido')
