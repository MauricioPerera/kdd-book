"""Oraculo congelado F2.

Escrito contra la firma de destino: un argumento de salida no se puede
quitar sin cambiar que devuelve la funcion, asi que el seed arranca rojo.
"""

import unittest

from target import agregar_inscripto


class AgregarInscriptoTest(unittest.TestCase):

    def test_devuelve_la_coleccion_con_el_nuevo(self):
        self.assertEqual(agregar_inscripto(('ana',), 'beto'), ('ana', 'beto'))

    def test_no_toca_la_entrada(self):
        original = ('ana',)
        agregar_inscripto(original, 'beto')
        self.assertEqual(original, ('ana',))

    def test_desde_vacio(self):
        self.assertEqual(agregar_inscripto((), 'ana'), ('ana',))

    def test_acepta_repetidos(self):
        self.assertEqual(agregar_inscripto(('ana',), 'ana'), ('ana', 'ana'))

    def test_devuelve_un_objeto_nuevo(self):
        original = ('ana',)
        self.assertIsNot(agregar_inscripto(original, "beto"), original)


if __name__ == '__main__':
    unittest.main()
