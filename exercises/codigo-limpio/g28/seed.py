"""Punto de partida G28: la condicion mezcla cuatro cosas en una linea."""


def estado_inscripcion(inscripto, pagado, vencido, cupos):
    if inscripto and pagado and vencido is False and cupos > 0:
        return 'confirmada'
    return 'pendiente'
