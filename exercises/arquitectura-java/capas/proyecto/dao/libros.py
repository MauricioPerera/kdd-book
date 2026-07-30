"""Capa de persistencia."""

LIBROS = [
    {'titulo': 'KDD', 'autor': 'Perera', 'anio': 2026},
    {'titulo': 'Contratos', 'autor': 'Bahit', 'anio': 2013},
]


class LibroDAO:
    def todos(self):
        return list(LIBROS)
