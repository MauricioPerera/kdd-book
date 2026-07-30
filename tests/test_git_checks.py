"""Los instrumentos de git contra repositorios reales, armados en temporales.

Se crean repos de verdad con commits y tags fechados en vez de simular la
salida de git. Un instrumento que solo se probo contra una cadena inventada no
sabe nada del formato real.
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..',
                                'instruments'))

import git_checks  # noqa: E402


def _opts(**kwargs):
    base = dict(max_dias=60, rama='master', tests=None, codigo=None)
    base.update(kwargs)
    return argparse.Namespace(**base)


class GitChecksTest(unittest.TestCase):

    def setUp(self):
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
        probadas = {n.split('_')[1] for n in dir(self) if n.startswith('test_')}
        self.assertEqual(set(git_checks.RULES) - probadas, set(),
                         'hay reglas de git sin prueba')

    def test_cadencia_detecta_y_acepta(self):
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
        repo = self._repo('tddn')
        self._commit(repo, 'x.py', 'x = 1\n', '2026-01-01T10:00:00')
        hallazgos = git_checks.check_tddorden(
            repo, _opts(tests='test_inexistente.py', codigo='x.py'))
        self.assertTrue(hallazgos)
        self.assertTrue(hallazgos[0][1], 'deberia ser no-verificable, no rojo')


if __name__ == '__main__':
    unittest.main()
