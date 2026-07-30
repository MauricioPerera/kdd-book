"""Oraculo congelado: la funcionalidad del proyecto.

No sabe nada de como se corre el proyecto ni de cuanto tarda. Esa ceguera es
lo que hace verificable a un contrato de nivel repo: el oraculo responde por la
funcionalidad y el instrumento por la propiedad del repositorio.
"""

import unittest

from tarifas import cupos_libres, precio_final


class CuposLibresTest(unittest.TestCase):

    def test_quedan_cupos(self):
        self.assertEqual(cupos_libres(40, 12), 28)

    def test_respeta_el_tope(self):
        self.assertEqual(cupos_libres(500, 0), 100)

    def test_sobrevendido_no_da_negativo(self):
        self.assertEqual(cupos_libres(40, 55), 0)

    def test_capacidad_cero(self):
        self.assertEqual(cupos_libres(0, 0), 0)


class PrecioFinalTest(unittest.TestCase):

    def test_sin_descuento(self):
        self.assertEqual(precio_final(100, 0), 100.0)

    def test_con_descuento(self):
        self.assertEqual(precio_final(100, 25), 75.0)

    def test_descuento_total(self):
        self.assertEqual(precio_final(100, 100), 0.0)

    def test_redondea(self):
        self.assertEqual(precio_final(99.99, 10), 89.99)

    def test_descuento_invalido(self):
        with self.assertRaises(ValueError):
            precio_final(100, 101)
        with self.assertRaises(ValueError):
            precio_final(100, -1)
