"""Series."""


def promedio(datos):
    años = [d for d in datos if d]
    return sum(años) / len(años)
