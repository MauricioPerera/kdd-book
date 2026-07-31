"""Servicio de saludo."""


def responder(ruta):
    if ruta == '/salud':
        return 200, 'ok'
    return 404, 'no esta'


def application(environ, start_response):
    # Alguien tiene que montar esto en un servidor: la app sola no escucha nada.
    codigo, cuerpo = responder(environ['PATH_INFO'])
    start_response(str(codigo), [])
    return [cuerpo.encode('utf-8')]
