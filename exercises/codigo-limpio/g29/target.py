"""Solucion G29: cada condicion se lee en positivo."""


def puede_inscribirse(cupos, bloqueado):
    if bloqueado:
        return False
    return cupos > 0
