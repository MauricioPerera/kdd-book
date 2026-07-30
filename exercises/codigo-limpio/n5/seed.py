"""Punto de partida N5: nombres de una letra en un ambito largo."""


def resumen_de_cupos(eventos):
    t = 0
    for e in eventos:
        if e['activo']:
            t += e['capacidad'] - e['inscriptos']
    if t < 0:
        t = 0
    if not eventos:
        return 0
    return t
