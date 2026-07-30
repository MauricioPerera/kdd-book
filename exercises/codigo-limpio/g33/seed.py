"""Punto de partida G33: la expresion de limite aparece tres veces."""


def rango_de_nivel(nivel):
    primero = nivel + 1
    ultimo = (nivel + 1) * 10
    etiqueta = str(nivel + 1)
    return (primero, ultimo, etiqueta)
