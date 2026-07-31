"""Pone `instruments/` y la raiz en el camino de importacion.

Existe por una regla de este mismo repositorio. Cada prueba hacia su propio
`sys.path.insert(...)` **antes** de importar el instrumento, y eso deja una
sentencia ejecutable entre los imports: `pep8_checks --rule imports` lo marcaba
en las doce suites, y tiene razon — PEP 8 pide que los imports vayan juntos y
arriba.

Importar este modulo hace el mismo trabajo y ES un import, asi que el bloque
queda entero. Se importa por su efecto, que es la unica razon por la que un
import puede no usarse.
"""

__all__ = ['instrumento']

import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

for camino in (os.path.join(RAIZ, 'instruments'), RAIZ):
    if camino not in sys.path:
        sys.path.insert(0, camino)


def instrumento(nombre):
    """Importa un instrumento por su nombre y lo devuelve.

    Existe para que las suites no tengan que importar por su EFECTO. Un
    `import contexto  # noqa` deja dos rojos en este mismo repositorio: `g12`
    marca el import sin usar y `g4` marca la supresion, que son dos
    instrumentos de dos autores pidiendo cosas incompatibles. Pasando por esta
    funcion el nombre se usa de verdad y no hace falta cancelar nada.
    """
    import importlib
    return importlib.import_module(nombre)
