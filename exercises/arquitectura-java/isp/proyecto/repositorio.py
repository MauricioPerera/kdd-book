"""Repositorio con toda la superficie que el sistema necesita."""


class RepositorioLibros:
    def buscar(self, titulo):
        return {'titulo': titulo}

    def guardar(self, libro):
        return True

    def borrar(self, titulo):
        return True

    def exportar(self):
        return []

    def reindexar(self):
        return True
