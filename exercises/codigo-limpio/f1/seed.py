"""Punto de partida del ejercicio F1: cinco argumentos posicionales."""


def crear_evento(nombre, fecha, ciudad, capacidad, precio):
    return {
        'nombre': nombre,
        'fecha': fecha,
        'ciudad': ciudad,
        'capacidad': capacidad,
        'precio': precio,
        'agotado': capacidad == 0,
    }
