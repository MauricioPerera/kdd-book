"""Solucion 143: cada paso del informe es un metodo corto."""


def _cupos_libres(evento):
    return max(0, evento['capacidad'] - evento['inscriptos'])


def _estado(libres):
    return 'completo' if libres == 0 else 'disponible'


def _encabezado(evento):
    return evento['nombre'].strip() + ' (' + evento['ciudad'].strip() + ')'


def informe_de_evento(evento):
    libres = _cupos_libres(evento)
    return '{} - {} - {} cupos'.format(
        _encabezado(evento), _estado(libres), libres)
