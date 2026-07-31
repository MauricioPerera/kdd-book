"""Acceso al almacen de pedidos."""

import os

DESTINO = 'postgres://app@db.interno:5432/tienda'


def describir():
    esquema = DESTINO.split('://')[0]
    return 'pedidos via {}'.format(esquema)
