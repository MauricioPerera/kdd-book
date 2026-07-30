"""Punto de partida: los campos no siguen la convencion de la tabla."""


class Libro:
    def __init__(self, titulo, escritor, publicado):
        self.titulo = titulo
        self.escritor = escritor
        self.publicado = publicado
