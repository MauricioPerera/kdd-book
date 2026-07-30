"""Punto de entrada del proyecto."""

import os
import py_compile
import sys
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))


def build():
    """Compila todos los modulos del proyecto."""
    for nombre in sorted(os.listdir(AQUI)):
        if nombre.endswith('.py'):
            py_compile.compile(os.path.join(AQUI, nombre), doraise=True)
    print('build OK')
    return 0


def test():
    """Descubre y corre toda la suite."""
    suite = unittest.defaultTestLoader.discover(AQUI, pattern='test_*.py',
                                                top_level_dir=AQUI)
    resultado = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if resultado.wasSuccessful() else 1


def coverage():
    """Informa que porcentaje de las lineas del codigo ejerce la suite."""
    import ast
    import io
    import trace
    rastreador = trace.Trace(count=1, trace=0,
                             ignoredirs=[sys.prefix, sys.exec_prefix])
    salida, sys.stdout = sys.stdout, io.StringIO()
    try:
        rastreador.runfunc(test)
    finally:
        sys.stdout = salida
    total = cubiertas = 0
    for nombre in sorted(os.listdir(AQUI)):
        if not nombre.endswith('.py') or nombre.startswith('test_') \
                or nombre == os.path.basename(__file__):
            continue
        ruta = os.path.join(AQUI, nombre)
        with open(ruta, encoding='utf-8') as fh:
            arbol = ast.parse(fh.read())
        lineas = {n.lineno for n in ast.walk(arbol) if isinstance(n, ast.stmt)
                  and not isinstance(n, (ast.FunctionDef, ast.ClassDef))}
        vistas = {n for (f, n) in rastreador.results().counts
                  if os.path.abspath(f) == ruta}
        total += len(lineas)
        cubiertas += len(lineas & vistas)
    print('cobertura: {:.1f}%'.format(100.0 * cubiertas / max(1, total)))
    return 0


TAREAS = {'build': build, 'test': test, 'coverage': coverage}


def main(argv):
    if len(argv) != 2 or argv[1] not in TAREAS:
        print('uso: python tareas.py [{}]'.format('|'.join(sorted(TAREAS))))
        return 2
    return TAREAS[argv[1]]()


if __name__ == '__main__':
    sys.exit(main(sys.argv))
