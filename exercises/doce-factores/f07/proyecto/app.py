"""Servicio de saludo."""

import http.server


def responder(ruta):
    if ruta == '/salud':
        return 200, 'ok'
    return 404, 'no esta'


class Manejador(http.server.BaseHTTPRequestHandler):

    def do_GET(self):
        codigo, cuerpo = responder(self.path)
        self.send_response(codigo)
        self.end_headers()
        self.wfile.write(cuerpo.encode('utf-8'))


def servir(puerto):
    servidor = http.server.HTTPServer(('', puerto), Manejador)
    servidor.serve_forever()
