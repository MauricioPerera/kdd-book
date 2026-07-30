"""Solucion G28: la condicion tiene nombre y el `if` se lee de un vistazo."""


def esta_confirmada(inscripto, pagado, vencido, cupos):
    return inscripto and pagado and vencido is False and cupos > 0


def estado_inscripcion(inscripto, pagado, vencido, cupos):
    if esta_confirmada(inscripto, pagado, vencido, cupos):
        return 'confirmada'
    return 'pendiente'
