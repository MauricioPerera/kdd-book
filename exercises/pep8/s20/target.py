"""Conversiones de temperatura."""


def a_fahrenheit(celsius):
    """Convierte grados Celsius a Fahrenheit."""
    return celsius * 9 / 5 + 32


def _redondear(valor):
    return round(valor, 1)
