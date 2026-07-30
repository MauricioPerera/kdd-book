"""Carrito del proyecto de ejemplo."""

ITEMS = []


def agregar(nombre):
    ITEMS.append(nombre)
    return len(ITEMS)


def total():
    return len(ITEMS)
