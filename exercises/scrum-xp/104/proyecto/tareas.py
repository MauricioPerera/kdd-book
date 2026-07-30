"""Punto de entrada del proyecto."""

import os
import sys
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))


def test():
    """Descubre y corre toda la suite."""
    suite = unittest.defaultTestLoader.discover(AQUI, pattern='test_*.py',
                                                top_level_dir=AQUI)
    resultado = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if resultado.wasSuccessful() else 1


TAREAS = {'test': test}


def main(argv):
    if len(argv) != 2 or argv[1] not in TAREAS:
        print('uso: python tareas.py [{}]'.format('|'.join(sorted(TAREAS))))
        return 2
    return TAREAS[argv[1]]()


if __name__ == '__main__':
    sys.exit(main(sys.argv))
