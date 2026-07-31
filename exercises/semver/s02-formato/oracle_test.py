"""Oraculo congelado: el proyecto sigue exponiendo __version__ como string.

El tipo de tecnica aqui es `refactor`: el comportamiento observable que no
cambia es que el modulo declare una version en texto. Lo que cambia —y mide
el instrumento— es el formato del string (X.Y.Z vs X.Y), que el oraculo no
inspecciona. Por eso el oraculo debe pasar tanto en el seed (`"1.2"`) como en
la solucion (`"1.2.0"`): ninguna de las dos rompe la invariante de que existe
una version publicada como literal de texto.
"""

import os
import re
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))


def texto(ruta):
    with open(os.path.join(AQUI, ruta), encoding='utf-8') as fh:
        return fh.read()


class VersionTest(unittest.TestCase):

    def _asignacion(self):
        return re.search(
            r'^\s*__version__\s*=\s*(["\'])(.*?)\1',
            texto('proyecto/version.py'),
            re.MULTILINE)

    def test_expone_version_como_string(self):
        match = self._asignacion()
        self.assertIsNotNone(
            match, '__version__ no esta asignado a un string literal')
        self.assertTrue(
            match.group(2), '__version__ no puede ser un string vacio')


if __name__ == '__main__':
    unittest.main()
