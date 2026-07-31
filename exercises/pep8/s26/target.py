"""Series."""


def promedio(datos):
    anios = [d for d in datos if d]
    return sum(anios) / len(anios)
