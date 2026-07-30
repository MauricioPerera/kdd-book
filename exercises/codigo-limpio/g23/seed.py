"""Punto de partida del ejercicio G23: una cadena if/elif discrimina por tipo."""


class Figura:
    def __init__(self, tipo, a, b):
        self.tipo = tipo
        self.a = a
        self.b = b


def crear_figura(tipo, a, b):
    if tipo not in ('rectangulo', 'triangulo', 'cuadrado'):
        raise KeyError(tipo)
    return Figura(tipo, a, b)


def area(figura):
    if figura.tipo == 'rectangulo':
        return figura.a * figura.b
    elif figura.tipo == 'triangulo':
        return figura.a * figura.b / 2
    elif figura.tipo == 'cuadrado':
        return figura.a * figura.a
    raise KeyError(figura.tipo)
