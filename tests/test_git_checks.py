"""Los instrumentos de git contra repositorios reales, armados en temporales.

Se crean repos de verdad con commits y tags fechados en vez de simular la
salida de git. Un instrumento que solo se probo contra una cadena inventada no
sabe nada del formato real.
"""

__all__ = ['GitChecksTest']

import argparse
import os
import shutil
import subprocess
import tempfile
import unittest

import contexto

git_checks = contexto.instrumento('git_checks')


def _opts(**kwargs):
    base = dict(max_dias=60, rama='master', tests=None, codigo=None)
    base.update(kwargs)
    return argparse.Namespace(**base)


class GitChecksTest(unittest.TestCase):
    """Cada regla de git contra repositorios armados en temporales."""

    def setUp(self):
        """SetUp."""
        self.raiz = tempfile.mkdtemp(prefix='kddbook-git-')
        self.addCleanup(shutil.rmtree, self.raiz, True)

    def _repo(self, nombre):
        ruta = os.path.join(self.raiz, nombre)
        os.makedirs(ruta)
        self._git(ruta, 'init', '-q', '-b', 'master')
        self._git(ruta, 'config', 'user.email', 'prueba@ejemplo.invalid')
        self._git(ruta, 'config', 'user.name', 'Prueba')
        return ruta

    def _git(self, repo, *args):
        entorno = dict(os.environ, GIT_TERMINAL_PROMPT='0')
        return subprocess.run(['git'] + list(args), cwd=repo, env=entorno,
                              capture_output=True, text=True)

    def _commit(self, repo, archivo, contenido, fecha):
        with open(os.path.join(repo, archivo), 'w', encoding='utf-8',
                  newline='\n') as fh:
            fh.write(contenido)
        self._git(repo, 'add', archivo)
        entorno = dict(os.environ, GIT_AUTHOR_DATE=fecha, GIT_COMMITTER_DATE=fecha)
        subprocess.run(['git', 'commit', '-q', '-m', 'commit ' + archivo],
                       cwd=repo, env=entorno, capture_output=True, text=True)

    def _tag(self, repo, nombre, fecha):
        entorno = dict(os.environ, GIT_AUTHOR_DATE=fecha, GIT_COMMITTER_DATE=fecha)
        subprocess.run(['git', 'tag', '-a', nombre, '-m', nombre],
                       cwd=repo, env=entorno, capture_output=True, text=True)

    def test_todas_las_reglas_tienen_prueba(self):
        """Todas las reglas tienen prueba."""
        probadas = {n.split('_')[1] for n in dir(self) if n.startswith('test_')}
        self.assertEqual(set(git_checks.RULES) - probadas, set(),
                         'hay reglas de git sin prueba')

    def test_cadencia_detecta_y_acepta(self):
        """Las dos mitades de `cadencia`: dispara sobre el caso roto y calla
        sobre el sano. Con una sola, un instrumento que nunca dispara
        pasaria igual.
        """
        verde = self._repo('cadv')
        self._commit(verde, 'a.txt', '1\n', '2026-01-01T10:00:00')
        self._tag(verde, 'v1', '2026-01-01T10:00:00')
        self._commit(verde, 'b.txt', '2\n', '2026-02-01T10:00:00')
        self._tag(verde, 'v2', '2026-02-01T10:00:00')
        self.assertEqual(git_checks.check_cadencia(verde, _opts(max_dias=60)), [])

        rojo = self._repo('cadr')
        self._commit(rojo, 'a.txt', '1\n', '2026-01-01T10:00:00')
        self._tag(rojo, 'v1', '2026-01-01T10:00:00')
        self._commit(rojo, 'b.txt', '2\n', '2026-09-01T10:00:00')
        self._tag(rojo, 'v2', '2026-09-01T10:00:00')
        hallazgos = git_checks.check_cadencia(rojo, _opts(max_dias=60))
        self.assertTrue(hallazgos)
        self.assertFalse(hallazgos[0][1], 'deberia ser rojo, no no-verificable')

    def test_cadencia_avisa_si_no_hay_con_que_medir(self):
        """Un solo tag no es una cadencia. Dar verde ahi seria mentir."""
        repo = self._repo('cad1')
        self._commit(repo, 'a.txt', '1\n', '2026-01-01T10:00:00')
        self._tag(repo, 'v1', '2026-01-01T10:00:00')
        hallazgos = git_checks.check_cadencia(repo, _opts())
        self.assertTrue(hallazgos)
        self.assertTrue(hallazgos[0][1], 'deberia ser no-verificable, no rojo')

    def test_repounico_detecta_y_acepta(self):
        """Las dos mitades de `repounico`: dispara sobre el caso roto y calla
        sobre el sano. Con una sola, un instrumento que nunca dispara
        pasaria igual.
        """
        verde = self._repo('repv')
        self._commit(verde, 'a.txt', '1\n', '2026-01-01T10:00:00')
        self.assertEqual(git_checks.check_repounico(verde, _opts()), [])

        rojo = self._repo('repr')
        self._commit(rojo, 'a.txt', '1\n', '2026-01-01T10:00:00')
        self._git(rojo, 'checkout', '-q', '-b', 'suelta')
        self._commit(rojo, 'b.txt', '2\n', '2026-01-02T10:00:00')
        self._git(rojo, 'checkout', '-q', 'master')
        self.assertTrue(git_checks.check_repounico(rojo, _opts()),
                        'no detecto la rama con commits sin integrar')

    def test_tddorden_detecta_y_acepta(self):
        """Las dos mitades de `tddorden`: dispara sobre el caso roto y calla
        sobre el sano. Con una sola, un instrumento que nunca dispara
        pasaria igual.
        """
        verde = self._repo('tddv')
        self._commit(verde, 'test_x.py', 'assert True\n', '2026-01-01T10:00:00')
        self._commit(verde, 'x.py', 'x = 1\n', '2026-01-02T10:00:00')
        self.assertEqual(
            git_checks.check_tddorden(verde, _opts(tests='test_x.py', codigo='x.py')),
            [])

        rojo = self._repo('tddr')
        self._commit(rojo, 'x.py', 'x = 1\n', '2026-01-01T10:00:00')
        self._commit(rojo, 'test_x.py', 'assert True\n', '2026-01-02T10:00:00')
        hallazgos = git_checks.check_tddorden(
            rojo, _opts(tests='test_x.py', codigo='x.py'))
        self.assertTrue(hallazgos)
        self.assertFalse(hallazgos[0][1], 'deberia ser rojo, no no-verificable')

    def test_tddorden_avisa_si_el_archivo_no_esta_en_el_historial(self):
        """Tddorden avisa si el archivo no esta en el historial."""
        repo = self._repo('tddn')
        self._commit(repo, 'x.py', 'x = 1\n', '2026-01-01T10:00:00')
        hallazgos = git_checks.check_tddorden(
            repo, _opts(tests='test_inexistente.py', codigo='x.py'))
        self.assertTrue(hallazgos)
        self.assertTrue(hallazgos[0][1], 'deberia ser no-verificable, no rojo')


    # ------------------------------------------------------------ codebase
    def test_codebase_acepta_un_repositorio_solo(self):
        """Codebase acepta un repositorio solo."""
        repo = self._repo('uno')
        self._commit(repo, 'a.py', 'X = 1\n', '2024-01-01T10:00:00')
        self.assertEqual(git_checks.check_codebase(repo, _opts()), [])

    def test_codebase_marca_el_directorio_sin_control_de_versiones(self):
        """Aca "no hay repositorio" es el hallazgo, no una imposibilidad.

        Es lo que separa esta regla de las otras tres: ellas miden propiedades
        DEL historial y sin historial no hay nada que medir; esta mide si hay
        historial. Por eso `main` se saltea la comprobacion previa para ella, y
        por eso la lista `SIN_REPO_ES_HALLAZGO` tiene que seguir nombrandola.
        """
        suelto = os.path.join(self.raiz, 'suelto')
        os.makedirs(suelto)
        hallazgos = git_checks.check_codebase(suelto, _opts())
        self.assertTrue(hallazgos, 'dio verde sobre un directorio sin git')
        self.assertFalse(hallazgos[0][1], 'lo reporto como no-verificable en vez de rojo')
        self.assertIn('control de versiones', hallazgos[0][0])

    def test_codebase_se_saltea_la_comprobacion_previa_de_main(self):
        """Sin eso, la regla saldria con exit 2 justo en el caso que debe marcar."""
        suelto = os.path.join(self.raiz, 'suelto2')
        os.makedirs(suelto)
        self.assertEqual(git_checks.main(['--rule', 'codebase', suelto]), 1)

    def test_codebase_detecta_otro_codebase_adentro(self):
        """Codebase detecta otro codebase adentro."""
        repo = self._repo('padre')
        self._commit(repo, 'a.py', 'X = 1\n', '2024-01-01T10:00:00')
        hijo = os.path.join(repo, 'vendor', 'lib')
        os.makedirs(hijo)
        self._git(hijo, 'init', '-q', '-b', 'master')
        hallazgos = git_checks.check_codebase(repo, _opts())
        self.assertTrue(hallazgos, 'no vio el repositorio anidado')
        self.assertIn('otro codebase', hallazgos[0][0])

    # ----------------------------------------------------------- releaseid
    def test_releaseid_acepta_una_marca_por_estado(self):
        """Releaseid acepta una marca por estado."""
        repo = self._repo('releases')
        self._commit(repo, 'a.py', 'X = 1\n', '2024-01-01T10:00:00')
        self._tag(repo, 'v1', '2024-01-01T10:00:00')
        self._commit(repo, 'b.py', 'Y = 2\n', '2024-02-01T10:00:00')
        self._tag(repo, 'v2', '2024-02-01T10:00:00')
        self.assertEqual(git_checks.check_releaseid(repo, _opts()), [])

    def test_releaseid_marca_el_repositorio_sin_ninguna_marca(self):
        """Releaseid marca el repositorio sin ninguna marca."""
        repo = self._repo('sin-tags')
        self._commit(repo, 'a.py', 'X = 1\n', '2024-01-01T10:00:00')
        hallazgos = git_checks.check_releaseid(repo, _opts())
        self.assertTrue(hallazgos)
        self.assertFalse(hallazgos[0][1], 'sin releases identificados es rojo, no exit 2')

    def test_releaseid_detecta_dos_identificadores_para_un_mismo_estado(self):
        """Lo que se repite en la practica no es el nombre del tag sino el estado."""
        repo = self._repo('dobles')
        self._commit(repo, 'a.py', 'X = 1\n', '2024-01-01T10:00:00')
        self._tag(repo, 'v1', '2024-01-01T10:00:00')
        self._tag(repo, 'v1.0.0', '2024-01-01T10:00:00')
        hallazgos = git_checks.check_releaseid(repo, _opts())
        self.assertTrue(hallazgos, 'no vio los dos tags sobre el mismo commit')
        self.assertIn('mismo estado', hallazgos[0][0])


if __name__ == '__main__':
    unittest.main()
