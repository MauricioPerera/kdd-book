"""Estado de un evento segun sus cupos.

Este archivo NO se toca: es el codigo que el instrumento va a mutar para ver
si la suite se entera.
"""


def estado_cupos(capacidad, inscriptos):
    if inscriptos < capacidad:
        return 'disponible'
    if inscriptos == capacidad:
        return 'completo'
    return 'sobrevendido'
