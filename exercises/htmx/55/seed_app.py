"""Aplicacion de ejemplo: devuelve la pagina entera o solo el fragmento."""

FILAS = [('Ana', 'confirmada'), ('Beto', 'pendiente')]


def _fragmento():
    filas = ''.join('<tr><td>{}</td><td>{}</td></tr>'.format(n, e) for n, e in FILAS)
    return '<tbody id="filas">{}</tbody>'.format(filas)


def _pagina():
    return '<html><body><table>{}</table></body></html>'.format(_fragmento())


def responder(ruta, cabeceras):
    """Devuelve (estado, cabeceras, cuerpo) para la peticion."""
    del ruta
    es_htmx = (cabeceras.get('HX-Request') or '').lower() == 'true'
    salida = {'Content-Type': 'text/html; charset=utf-8'}
    salida['Vary'] = 'HX-Request'
    return 200, salida, (_fragmento() if es_htmx else _pagina())
