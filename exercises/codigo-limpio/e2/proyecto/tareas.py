"""Solucion de referencia del ejercicio E2: punto de entrada unico.

`python tareas.py test` descubre y corre toda la suite en un solo paso, sin
que nadie tenga que recordar rutas ni patrones.
"""

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


TAREAS = {'build': build, 'test': test}


def main(argv):
    if len(argv) != 2 or argv[1] not in TAREAS:
        print('uso: python tareas.py [{}]'.format('|'.join(sorted(TAREAS))))
        return 2
    return TAREAS[argv[1]]()


if __name__ == '__main__':
    sys.exit(main(sys.argv))
