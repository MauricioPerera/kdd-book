"""Solucion N5: el largo del nombre acompana al largo del ambito."""


def resumen_de_cupos(eventos):
    libres = 0
    for evento in eventos:
        if evento['activo']:
            libres += evento['capacidad'] - evento['inscriptos']
    if libres < 0:
        libres = 0
    if not eventos:
        return 0
    return libres
