"""Solucion G33: el limite se calcula una vez y tiene nombre."""


def rango_de_nivel(nivel):
    siguiente = nivel + 1
    return (siguiente, siguiente * 10, str(siguiente))
