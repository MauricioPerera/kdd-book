"""Oraculo congelado: double existe y lleva un ejemplo rustdoc con fence.

Tecnica de tipo `refactor`: el artefacto observable es que exista
`pub fn double` y que siga teniendo un ejemplo en un bloque de codigo
rustdoc (`///` con ``` ``` ```). El instrumento mide que el ejemplo use `?`
en vez de `.unwrap()`/`try!()`. El oraculo no inspecciona que operador se
usa: basta con que el ejemplo exista. El atajo de borrar el ejemplo deja
el oraculo en rojo (no hay fence) mientras el instrumento, que no ve el
ejemplo, no lo marca.
"""
import os
import re
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))


def texto(ruta='proyecto/lib.rs'):
    with open(os.path.join(AQUI, ruta), encoding='utf-8') as fh:
        return fh.read()


_FENCE = re.compile(r'///[^\n]*```')


class DoubleTest(unittest.TestCase):

    def test_existe_funcion(self):
        self.assertRegex(texto(), r'pub\s+fn\s+double\s*\(')

    def test_tiene_ejemplo_rustdoc(self):
        self.assertRegex(texto(), _FENCE)


if __name__ == '__main__':
    unittest.main()
