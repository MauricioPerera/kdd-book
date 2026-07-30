"""Punto de partida 142: la condicion se lee de una sola vez o no se lee."""


def admite_inscripcion(cupos, abierto, pagado, bloqueado):
    return (cupos > 0 and abierto) and (pagado or not bloqueado)
