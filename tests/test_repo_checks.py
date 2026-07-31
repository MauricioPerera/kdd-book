"""Cada instrumento de nivel repo contra un proyecto rojo y uno verde.

Estos checks ejecutan comandos de verdad, asi que las pruebas arman proyectos
minimos en un directorio temporal en vez de simular. Si el instrumento se
puede enganar con un proyecto de juguete, se puede enganar con uno real.
"""

import argparse
import os
import shutil
import tempfile
import unittest

import contexto

repo_checks = contexto.instrumento('repo_checks')


TAREAS_COMPLETO = '''
import os, sys, unittest, py_compile
AQUI = os.path.dirname(os.path.abspath(__file__))
def build():
    for n in sorted(os.listdir(AQUI)):
        if n.endswith('.py'):
            py_compile.compile(os.path.join(AQUI, n), doraise=True)
    return 0
def test():
    suite = unittest.defaultTestLoader.discover(AQUI, pattern='test_*.py',
                                                top_level_dir=AQUI)
    return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1
def coverage():
    import ast, io, trace
    tr = trace.Trace(count=1, trace=0, ignoredirs=[sys.prefix, sys.exec_prefix])
    salida, sys.stdout = sys.stdout, io.StringIO()
    try:
        tr.runfunc(test)
    finally:
        sys.stdout = salida
    fuente = os.path.join(AQUI, 'fuente.py')
    with open(fuente, encoding='utf-8') as fh:
        arbol = ast.parse(fh.read())
    lineas = {n.lineno for n in ast.walk(arbol) if isinstance(n, ast.stmt)
              and not isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    vistas = {n for (f, n) in tr.results().counts if os.path.abspath(f) == fuente}
    print('{:.1f}%'.format(100.0 * len(lineas & vistas) / max(1, len(lineas))))
    return 0
TAREAS = {__TAREAS__}
def main(argv):
    if len(argv) != 2 or argv[1] not in TAREAS:
        return 2
    return TAREAS[argv[1]]()
if __name__ == '__main__':
    sys.exit(main(sys.argv))
'''.lstrip()


def _tareas(*nombres):
    """Punto de entrada que expone solo las tareas pedidas.

    Las variantes se derivan de la lista, no de un `replace` sobre el texto:
    cuando se agrego la tarea `coverage`, los `replace` dejaron de coincidir y
    las variantes "rojas" quedaron identicas a la verde sin que nada avisara.
    """
    registro = ', '.join("'{0}': {0}".format(n) for n in nombres)
    return TAREAS_PLANTILLA.replace('{__TAREAS__}', '{' + registro + '}')


TAREAS_PLANTILLA = TAREAS_COMPLETO
TAREAS_COMPLETO = _tareas('build', 'test', 'coverage')
TAREAS_SIN_TEST = _tareas('build', 'coverage')

FUENTE = 'def doble(n):\n    return n * 2\n\n\ndef triple(n):\n    return n * 3\n'

TEST_COMPLETO = ('import unittest\nfrom fuente import doble, triple\n\n\n'
                 'class T(unittest.TestCase):\n'
                 '    def test_doble(self):\n        self.assertEqual(doble(2), 4)\n'
                 '    def test_triple(self):\n        self.assertEqual(triple(2), 6)\n')

TEST_QUE_NO_TOCA_LA_FUENTE = ('import unittest\n\n\nclass T(unittest.TestCase):\n'
                              '    def test_nada(self):\n        self.assertTrue(True)\n')

TEST_LENTO = ('import time\nimport unittest\nfrom fuente import doble\n\n\n'
              'class T(unittest.TestCase):\n'
              '    def test_doble(self):\n        time.sleep(0.4)\n'
              '        self.assertEqual(doble(2), 4)\n')


def _opts(**kwargs):
    base = dict(min_tests=1, max_seconds=5.0, min_coverage=80.0, max_line=100)
    base.update(kwargs)
    return argparse.Namespace(**base)


class RepoChecksTest(unittest.TestCase):

    def setUp(self):
        self.raiz = tempfile.mkdtemp(prefix='kddbook-')
        self.addCleanup(shutil.rmtree, self.raiz, True)

    def _proyecto(self, nombre, tareas, fuente=FUENTE, prueba=TEST_COMPLETO):
        ruta = os.path.join(self.raiz, nombre)
        os.makedirs(ruta, exist_ok=True)
        for archivo, contenido in (('tareas.py', tareas), ('fuente.py', fuente),
                                   ('test_fuente.py', prueba)):
            with open(os.path.join(ruta, archivo), 'w', encoding='utf-8',
                      newline='\n') as fh:
                fh.write(contenido)
        return os.path.join(ruta, 'tareas.py')

    def test_todas_las_reglas_tienen_prueba(self):
        probadas = {n[len('test_'):].split('_')[0] for n in dir(self)
                    if n.startswith('test_') and n[len('test_'):].split('_')[0]
                    in repo_checks.RULES}
        self.assertEqual(probadas, set(repo_checks.RULES),
                         'hay reglas de nivel repo sin prueba')

    def test_aislamiento_detecta_y_acepta(self):
        verde = self._proyecto('aisv', TAREAS_COMPLETO)
        self.assertEqual(repo_checks.check_aislamiento(verde, _opts()), [])

        # Una prueba que solo pasa si otra corrio antes y le dejo el estado.
        raiz = os.path.join(self.raiz, 'aisr')
        self._proyecto('aisr', TAREAS_COMPLETO)
        for archivo, contenido in (
                ('estado.py', 'VISTOS = []\n'),
                ('test_a_deja.py',
                 'import unittest\nfrom estado import VISTOS\n\n\n'
                 'class A(unittest.TestCase):\n'
                 '    def test_deja(self):\n'
                 "        VISTOS.append('a')\n"
                 '        self.assertTrue(VISTOS)\n'),
                ('test_b_depende.py',
                 'import unittest\nfrom estado import VISTOS\n\n\n'
                 'class B(unittest.TestCase):\n'
                 '    def test_depende(self):\n'
                 '        self.assertTrue(VISTOS)\n')):
            with open(os.path.join(raiz, archivo), 'w', encoding='utf-8',
                      newline='\n') as fh:
                fh.write(contenido)
        rojo = os.path.join(raiz, 'tareas.py')
        self.assertTrue(repo_checks.check_aislamiento(rojo, _opts()),
                        'no detecto la prueba que depende de otra')

    def test_e1_detecta_y_acepta(self):
        verde = self._proyecto('e1v', TAREAS_COMPLETO)
        self.assertEqual(repo_checks.check_e1(verde, _opts()), [])
        rojo = self._proyecto('e1r', _tareas('test', 'coverage'))
        self.assertTrue(repo_checks.check_e1(rojo, _opts()))

    def test_e2_detecta_y_acepta(self):
        verde = self._proyecto('e2v', TAREAS_COMPLETO)
        self.assertEqual(repo_checks.check_e2(verde, _opts(min_tests=2)), [])
        rojo = self._proyecto('e2r', TAREAS_SIN_TEST)
        self.assertTrue(repo_checks.check_e2(rojo, _opts(min_tests=2)))

    def test_e2_rechaza_un_paso_que_no_prueba_nada(self):
        """Un `test` que sale 0 sin correr nada es el modo de fallo silencioso."""
        rojo = self._proyecto('e2n', TAREAS_COMPLETO, prueba=TEST_QUE_NO_TOCA_LA_FUENTE)
        self.assertTrue(repo_checks.check_e2(rojo, _opts(min_tests=5)))

    def test_t1_detecta_y_acepta(self):
        verde = self._proyecto('t1v', TAREAS_COMPLETO)
        self.assertEqual(repo_checks.check_t1(verde, _opts(min_coverage=80)), [])
        rojo = self._proyecto('t1r', TAREAS_COMPLETO, prueba=TEST_QUE_NO_TOCA_LA_FUENTE)
        self.assertTrue(repo_checks.check_t1(rojo, _opts(min_coverage=80)))

    def test_t1_no_castiga_los_docstrings(self):
        """Una cobertura que baja al documentar esta midiendo mal."""
        documentada = FUENTE.replace('def doble(n):\n', 'def doble(n):\n    """Doble."""\n')
        documentada = documentada.replace('def triple(n):\n',
                                          'def triple(n):\n    """Triple."""\n')
        verde = self._proyecto('t1d', TAREAS_COMPLETO, fuente=documentada)
        self.assertEqual(repo_checks.check_t1(verde, _opts(min_coverage=100)), [])

    def test_t2_detecta_y_acepta(self):
        verde = self._proyecto('t2v', TAREAS_COMPLETO)
        self.assertEqual(repo_checks.check_t2(verde, _opts()), [])
        sin_tarea = _tareas('build', 'test')
        self.assertTrue(repo_checks.check_t2(self._proyecto('t2r', sin_tarea), _opts()))

    def test_t2_rechaza_una_tarea_que_no_informa_numero(self):
        """Una tarea `coverage` que sale 0 sin decir un porcentaje no mide nada."""
        muda = TAREAS_COMPLETO.replace("    print('{:.1f}%'.format(",
                                       "    ('{:.1f}'.format(")
        muda = muda.replace('100.0 * len(lineas & vistas) / max(1, len(lineas))))',
                            '100.0 * len(lineas & vistas) / max(1, len(lineas))))\n    print("listo")')
        self.assertTrue(repo_checks.check_t2(self._proyecto('t2m', muda), _opts()))

    def test_t9_detecta_y_acepta(self):
        verde = self._proyecto('t9v', TAREAS_COMPLETO)
        self.assertEqual(repo_checks.check_t9(verde, _opts(max_seconds=30)), [])
        rojo = self._proyecto('t9r', TAREAS_COMPLETO, prueba=TEST_LENTO)
        self.assertTrue(repo_checks.check_t9(rojo, _opts(max_seconds=0.2)))

    def test_g24_detecta_y_acepta(self):
        verde = self._proyecto('g24v', TAREAS_COMPLETO)
        self.assertEqual(repo_checks.check_g24(verde, _opts()), [])
        rojo = self._proyecto('g24r', TAREAS_COMPLETO,
                              fuente='def f():\n    return "' + 'x' * 120 + '"   \n')
        self.assertTrue(repo_checks.check_g24(rojo, _opts(max_line=100)))


if __name__ == '__main__':
    unittest.main()
