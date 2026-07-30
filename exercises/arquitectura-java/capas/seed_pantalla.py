"""Capa de presentacion: se saltea el servicio y va directo al DAO."""

from dao.libros import LibroDAO


def pantalla_de_libros():
    dao = LibroDAO()
    return ' | '.join(sorted(libro['titulo'] for libro in dao.todos()))
