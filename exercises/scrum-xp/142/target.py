"""Solucion 142: cada parte del calculo tiene nombre.

Los nombres intermedios no tienen que ser elocuentes para que la tecnica
quede aplicada: lo que el instrumento mide es que ninguna expresion
acumule mas operadores de los permitidos.
"""


def admite_inscripcion(cupos, abierto, pagado, bloqueado):
    hay_lugar = cupos > 0
    disponible = hay_lugar and abierto
    habilitado = pagado or not bloqueado
    return disponible and habilitado
