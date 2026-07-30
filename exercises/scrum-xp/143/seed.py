"""Punto de partida 143: un metodo que hace todo el recorrido."""


def informe_de_evento(evento):
    nombre = evento['nombre'].strip()
    ciudad = evento['ciudad'].strip()
    capacidad = evento['capacidad']
    inscriptos = evento['inscriptos']
    libres = capacidad - inscriptos
    if libres < 0:
        libres = 0
    if libres == 0:
        estado = 'completo'
    else:
        estado = 'disponible'
    encabezado = nombre + ' (' + ciudad + ')'
    detalle = str(libres) + ' cupos'
    return encabezado + ' - ' + estado + ' - ' + detalle
