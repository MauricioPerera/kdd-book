"""Oraculo congelado del ejercicio G23.

Fija el comportamiento de `crear_figura` y `area` sin decir una palabra sobre
como se despacha. Esa ceguera es el punto: pasa igual con la cadena if/elif y
con el polimorfismo, asi que no puede decir si la tecnica se aplico. Eso lo
decide el instrumento.
"""

import unittest

from target import area, crear_figura


class AreaTest(unittest.TestCase):

    def test_rectangulo(self):
        self.assertEqual(area(crear_figura('rectangulo', 3, 4)), 12)

    def test_triangulo(self):
        self.assertEqual(area(crear_figura('triangulo', 3, 4)), 6)

    def test_cuadrado_ignora_el_segundo_lado(self):
        self.assertEqual(area(crear_figura('cuadrado', 5, 99)), 25)

    def test_tipo_desconocido_levanta_keyerror(self):
        with self.assertRaises(KeyError):
            crear_figura('trapecio', 1, 2)

    def test_acepta_medidas_decimales(self):
        self.assertAlmostEqual(area(crear_figura('triangulo', 2.5, 4)), 5.0)

    def test_medidas_cero_dan_area_cero(self):
        self.assertEqual(area(crear_figura('rectangulo', 0, 7)), 0)


if __name__ == '__main__':
    unittest.main()
