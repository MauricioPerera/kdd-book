"""Punto de partida del ejercicio E2: probar necesita pasos manuales.

El punto de entrada solo sabe generar. Para correr las pruebas hay que
acordarse del comando, del patron y del directorio, o sea que probar cuesta
mas de un paso: exactamente lo que E2 senala.
"""

import os
import py_compile
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))


def build():
    """Compila todos los modulos del proyecto."""
    for nombre in sorted(os.listdir(AQUI)):
        if nombre.endswith('.py'):
            py_compile.compile(os.path.join(AQUI, nombre), doraise=True)
    print('build OK')
    return 0


TAREAS = {'build': build}


def main(argv):
    if len(argv) != 2 or argv[1] not in TAREAS:
        print('uso: python tareas.py [{}]'.format('|'.join(sorted(TAREAS))))
        print('para probar: cd proyecto && python -m unittest discover -p "test_*.py"')
        return 2
    return TAREAS[argv[1]]()


if __name__ == '__main__':
    sys.exit(main(sys.argv))
