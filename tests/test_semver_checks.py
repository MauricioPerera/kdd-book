"""Los instrumentos de semver contra proyectos rojos y verdes.

Tres reglas (formato, pre-release, build), cada una la contrapositiva de un
articulo del SemVer 2.0.0 que se puede exigir como invariante sobre el string
de version. La prueba arma el proyecto minimo que la contradice y el minimo
que la respeta.
"""

__all__ = ['SemverChecksTest']

import argparse
import os
import shutil
import tempfile
import unittest

import contexto

S = contexto.instrumento('semver_checks')


class SemverChecksTest(unittest.TestCase):
    """Cada regla de semver contra un proyecto roto y uno sano."""

    def setUp(self):
        """SetUp."""
        self.raiz = tempfile.mkdtemp(prefix='kddbook-semver-')
        self.addCleanup(shutil.rmtree, self.raiz, True)

    def _proyecto(self, archivos):
        for nombre, contenido in archivos.items():
            ruta = os.path.join(self.raiz, nombre.replace('/', os.sep))
            os.makedirs(os.path.dirname(ruta), exist_ok=True)
            with open(ruta, 'w', encoding='utf-8', newline='\n') as fh:
                fh.write(contenido)
        return self.raiz

    def _opts(self, **kwargs):
        base = dict(proyecto=self.raiz)
        base.update(kwargs)
        return argparse.Namespace(**base)

    def _correr(self, regla, archivos, **kwargs):
        self._proyecto(archivos)
        return S.RULES[regla][0](S._fuentes(self.raiz), self._opts(**kwargs))

    def test_todas_las_reglas_tienen_prueba(self):
        """Todas las reglas tienen prueba."""
        metodos = [n for n in dir(self) if n.startswith('test_')]
        sin_prueba = [r for r in S.RULES
                      if not any(m.startswith('test_' + r.replace('-', '_'))
                                 for m in metodos)]
        self.assertEqual(sin_prueba, [], 'hay reglas de semver sin prueba')

    def test_todas_las_funciones_check_estan_registradas(self):
        """Todas las funciones check estan registradas."""
        definidas = {n[len('check_'):].replace('_', '-') for n in dir(S)
                     if n.startswith('check_')}
        self.assertEqual(definidas - set(S.RULES), set(),
                         'hay checks escritos que el instrumento no puede ejecutar')

    # --------------------------------------------------------------- formato
    def test_formato_detecta_y_acepta(self):
        """Las dos mitades de `formato`: dispara sobre el caso roto y calla
        sobre el sano. Con una sola, un instrumento que nunca dispara pasaria
        igual.
        """
        rojo = self._correr('formato',
                            {'version.py': '__version__ = "1.2"\n'})
        self.assertTrue(rojo, 'no detecto el formato roto X.Y')
        self.assertIn('__version__', rojo[0][2])

        verde = self._correr('formato',
                             {'version.py': '__version__ = "1.2.0"\n'})
        self.assertEqual(verde, [], 'marco una version X.Y.Z valida')

    def test_formato_rechaza_ceros_iniciales(self):
        """Un componente con cero inicial (`01.0.0`) rompe el formato X.Y.Z."""
        rojo = self._correr('formato',
                            {'version.py': '__version__ = "01.0.0"\n'})
        self.assertTrue(rojo, 'no detecto el cero inicial en el componente')

    def test_formato_acepta_ceros_solitarios(self):
        """Un componente que es exactamente `0` no tiene cero inicial."""
        verde = self._correr('formato',
                             {'version.py': '__version__ = "0.0.1"\n'})
        self.assertEqual(verde, [], 'marque `0` como cero inicial')

    def test_formato_rechaza_sufijo_prerelease(self):
        """Un sufijo pre-release/ build no entra en el formato de la normal."""
        self.assertTrue(self._correr('formato',
                                     {'version.py': '__version__ = "1.0.0-alpha.1"\n'}),
                        'no marco un pre-release como formato roto')

    # ----------------------------------------------------------- pre-release
    def test_prerelease_detecta_y_acepta(self):
        """Las dos mitades de `prerelease`: dispara sobre el caso roto y calla
        sobre el sano.
        """
        rojo = self._correr('prerelease',
                            {'version.py': '__version__ = "1.0.0-alpha.01"\n'})
        self.assertTrue(rojo, 'no detecto el cero inicial en el identificador numerico')
        self.assertIn('01', rojo[0][2])

        verde = self._correr('prerelease',
                             {'version.py': '__version__ = "1.0.0-alpha.1"\n'})
        self.assertEqual(verde, [], 'marque un pre-release bien formado')

    def test_prerelease_acepta_build_metadata_al_lado(self):
        """Un build metadata valido al lado del pre-release no lo invalida."""
        verde = self._correr('prerelease',
                             {'version.py': '__version__ = "1.0.0-alpha.1+20130313144700"\n'})
        self.assertEqual(verde, [], 'marque un pre-release con build metadata valido')

    # ------------------------------------------------------------------- build
    def test_build_detecta_y_acepta(self):
        """Las dos mitades de `build`: dispara sobre el caso roto y calla sobre
        el sano.
        """
        rojo = self._correr('build',
                            {'version.py': '__version__ = "1.0.0+bad id"\n'})
        self.assertTrue(rojo, 'no detecto el identificador de build invalido')
        self.assertIn('bad id', rojo[0][2])

        verde = self._correr('build',
                             {'version.py': '__version__ = "1.0.0+20130313144700"\n'})
        self.assertEqual(verde, [], 'marque un build metadata valido')

    def test_build_acepta_ceros_iniciales_numericos(self):
        """A diferencia del pre-release, el build SI puede tener ceros iniciales."""
        verde = self._correr('build',
                             {'version.py': '__version__ = "1.0.0+001"\n'})
        self.assertEqual(verde, [], 'marque un identificador numerico de build con cero inicial')

    # ------------------------------------------------------------- alcance
    def test_las_pruebas_del_proyecto_medido_no_cuentan(self):
        """Un string de version de mentira en un fixture es lo que un fixture
        debe tener."""
        verde = self._correr('formato',
                             {'version.py': '__version__ = "1.2.0"\n',
                              'test_version.py': '__version__ = "1.2"\n'})
        self.assertEqual(verde, [], 'marque una version rota viva solo en tests')


if __name__ == '__main__':
    unittest.main()
