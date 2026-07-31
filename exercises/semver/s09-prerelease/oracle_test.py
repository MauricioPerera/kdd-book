"""Oraculo congelado: el proyecto sigue exponiendo __version__ como string
con un sufijo pre-release.

Tecnica de tipo `refactor`: el artefacto observable es que exista una version
publicada como literal de texto, y que declare un sufijo pre-release. Lo que
cambia —y mide el instrumento— es la validez de los identificadores
pre-release (un `alpha.01` con cero inicial deja de ser valido SemVer), algo
que el oraculo no inspecciona. Por eso pasa tanto en el seed
(`"1.0.0-alpha.01"`) como en la solucion (`"1.0.0-alpha.1"`): ambas declaran
una version como string con sufijo pre-release; ninguna cambia la invariante.

Regresion: la primera version de este oraculo solo pedia que `__version__`
fuera un string no vacio, sin exigir que siguiera siendo un pre-release. Eso
dejaba pasar un atajo que el spec prohibe explicitamente —reemplazar el
sufijo pre-release por build metadata (`1.0.0+alpha.1`)— porque un string no
vacio sin `-` tambien cumplia esa unica asercion, y la regla `prerelease` del
instrumento tampoco objeta nada si no hay ningun sufijo pre-release que
medir. El oraculo ahora exige la presencia del sufijo `-...` para que ese
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

    def test_sigue_declarando_un_prerelease(self):
        match = self._asignacion()
        self.assertIsNotNone(
            match, '__version__ no esta asignado a un string literal')
        version = match.group(2)
        base = version.split('+', 1)[0]
        self.assertIn(
            '-', base,
            '__version__ dejo de declarar un sufijo pre-release: la tecnica '
            'es sobre el formato del pre-release, no sobre sacarlo')


if __name__ == '__main__':
    unittest.main()
