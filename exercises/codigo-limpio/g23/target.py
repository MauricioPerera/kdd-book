"""Solucion de referencia del ejercicio G23: cada figura sabe calcular su area.

La cadena if/elif desaparece dos veces: en `area`, porque cada clase responde
por si misma, y en `crear_figura`, porque la eleccion es una busqueda en un
registro y no una discriminacion escrita a mano.
"""


class Rectangulo:
    def __init__(self, a, b):
        self.a = a
        self.b = b

    def area(self):
        return self.a * self.b


class Triangulo:
    def __init__(self, a, b):
        self.a = a
        self.b = b

    def area(self):
        return self.a * self.b / 2


class Cuadrado:
    def __init__(self, a, b):
        self.a = a
        self.b = b

    def area(self):
        return self.a * self.a


_FIGURAS = {
    'rectangulo': Rectangulo,
    'triangulo': Triangulo,
    'cuadrado': Cuadrado,
}


def crear_figura(tipo, a, b):
    return _FIGURAS[tipo](a, b)


def area(figura):
    return figura.area()
