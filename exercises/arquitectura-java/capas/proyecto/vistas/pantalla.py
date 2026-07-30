"""Capa de presentacion: solo conoce a su vecino inmediato."""

from servicios.libros import ServicioLibros


def pantalla_de_libros():
    return ' | '.join(ServicioLibros().titulos_ordenados())
