"""Capa de negocio."""

from dao.libros import LibroDAO


class ServicioLibros:
    def __init__(self, dao=None):
        self.dao = dao or LibroDAO()

    def titulos_ordenados(self):
        return sorted(libro['titulo'] for libro in self.dao.todos())
