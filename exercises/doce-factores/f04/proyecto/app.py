"""Acceso al almacen de pedidos."""

import os

DESTINO = os.environ['DATABASE_URL']


def describir():
    esquema = DESTINO.split('://')[0]
    return 'pedidos via {}'.format(esquema)
