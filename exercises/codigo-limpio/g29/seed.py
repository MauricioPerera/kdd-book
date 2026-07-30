"""Punto de partida G29: la logica se lee toda en negativo.

`not cupos <= 0` es exactamente `cupos > 0`, asi que el comportamiento es el
mismo que el de la solucion: lo unico que cambia es cuanto cuesta leerlo. Esa
equivalencia es lo que hace de esto un refactor y no un arreglo.
"""


def puede_inscribirse(cupos, bloqueado):
    if not bloqueado:
        if not cupos <= 0:
            return True
    return False
