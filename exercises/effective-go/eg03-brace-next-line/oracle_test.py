"""Oraculo congelado: el programa Go conserva su esqueleto de "hola mundo".

La tecnica aqui es `refactor`: lo que cambia es una convencion de formato
(tabs vs espacios, parentesis, posicion de la llave). El comportamiento
observable no cambia: el programa sigue imprimiendo "hola". El oraculo verifica
esas propiedades estructurales que deben ser invariantes tanto en el seed como
en la solucion.
"""

import os
import re
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))


def texto(ruta):
    with open(os.path.join(AQUI, ruta), encoding='utf-8') as fh:
        return fh.read()


class EstructuraTest(unittest.TestCase):

    def _codigo(self):
        return texto('proyecto/main.go')

    def test_tiene_package_main(self):
        self.assertIn('package main', self._codigo(),
                      'el programa debe declarar package main')

    def test_tiene_func_main(self):
        self.assertRegex(self._codigo(), r'\bfunc\s+main\s*\(\s*\)',
                         'el programa debe declarar func main()')

    def test_imprime_hola(self):
        self.assertIn('"hola"', self._codigo(),
                      'el programa debe imprimir el mensaje "hola"')

    def test_usa_fmt_Println(self):
        self.assertIn('fmt.Println', self._codigo(),
                      'el programa debe usar fmt.Println')


if __name__ == '__main__':
    unittest.main()
