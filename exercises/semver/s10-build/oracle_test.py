"""Oraculo congelado: el proyecto sigue exponiendo __version__ como string
con build metadata.

Tecnica de tipo `refactor`: el artefacto observable es que exista una version
publicada como literal de texto, y que declare build metadata. Lo que cambia
—y mide el instrumento— es la validez de los identificadores de build
metadata (un `1.0.0+bad id` con un espacio deja de ser valido SemVer), algo
que el oraculo no inspecciona. Por eso pasa tanto en el seed
(`"1.0.0+bad id"`) como en la solucion (`"1.0.0+20130313144700"`): ambas
declaran una version como string con build metadata; ninguna rompe la
invariante.

Regresion: la primera version de este oraculo solo pedia que `__version__`
fuera un string no vacio, sin exigir que siguiera declarando build metadata.
El spec prohibe explicitamente "eliminar el build metadata" como atajo, pero
un string no vacio sin `+` tambien cumplia esa unica asercion, y la regla
`build` del instrumento tampoco objeta nada si no hay ningun build metadata
que medir. El oraculo ahora exige la presencia del sufijo `+...` para que ese
atajo se note.
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

    def test_sigue_declarando_build_metadata(self):
        match = self._asignacion()
        self.assertIsNotNone(
            match, '__version__ no esta asignado a un string literal')
        self.assertIn(
            '+', match.group(2),
            '__version__ dejo de declarar build metadata: la tecnica es '
            'sobre el formato del build metadata, no sobre sacarlo')


if __name__ == '__main__':
    unittest.main()
