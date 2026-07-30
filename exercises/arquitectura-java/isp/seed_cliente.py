"""Punto de partida: el buscador depende de todo el repositorio."""

from repositorio import RepositorioLibros


class Buscador:
    def por_titulo(self, repo: RepositorioLibros, titulo):
        return repo.buscar(titulo)
