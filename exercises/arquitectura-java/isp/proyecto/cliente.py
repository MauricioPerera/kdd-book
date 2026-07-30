"""Solucion: el buscador depende solo de lo que usa."""


class SoloBusqueda:
    def buscar(self, titulo):
        raise NotImplementedError


class Buscador:
    def por_titulo(self, repo: SoloBusqueda, titulo):
        return repo.buscar(titulo)
