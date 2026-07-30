"""Oraculo congelado del ejercicio E2.

Prueba la funcionalidad del proyecto, no la forma de correrlo. Esa separacion
es lo que hace verificable a un contrato de nivel repo: el oraculo dice que el
proyecto sigue funcionando, y el instrumento dice si probarlo se volvio un solo
paso. Ninguno de los dos puede responder por el otro.
"""

import unittest

from tarifas import cupos_disponibles, duracion_en_horas, precio_final


class PrecioFinalTest(unittest.TestCase):

    def test_sin_descuento(self):
        self.assertEqual(precio_final(100, 0), 100.0)

    def test_con_descuento(self):
        self.assertEqual(precio_final(100, 25), 75.0)

    def test_redondea_a_dos_decimales(self):
        self.assertEqual(precio_final(99.99, 10), 89.99)

    def test_descuento_total(self):
        self.assertEqual(precio_final(100, 100), 0.0)

    def test_descuento_invalido(self):
        with self.assertRaises(ValueError):
            precio_final(100, 101)
        with self.assertRaises(ValueError):
            precio_final(100, -1)


class CuposTest(unittest.TestCase):

    def test_quedan_cupos(self):
        self.assertEqual(cupos_disponibles(40, 12), 28)

    def test_sobrevendido_no_da_negativo(self):
        self.assertEqual(cupos_disponibles(40, 55), 0)

    def test_exactamente_lleno(self):
        self.assertEqual(cupos_disponibles(40, 40), 0)


class DuracionTest(unittest.TestCase):

    def test_una_hora(self):
        self.assertEqual(duracion_en_horas(3600), 1.0)

    def test_media_hora(self):
        self.assertEqual(duracion_en_horas(1800), 0.5)

    def test_redondea_a_un_decimal(self):
        self.assertEqual(duracion_en_horas(5000), 1.4)


if __name__ == '__main__':
    unittest.main()
