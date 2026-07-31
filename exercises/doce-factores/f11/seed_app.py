"""Registro de pedidos."""

import logging

FORMATO = '%(levelname)s %(name)s %(message)s'


def configurar():
    logging.basicConfig(filename='pedidos.log', format=FORMATO, level=logging.INFO)


def mensaje_de(numero):
    return 'pedido {} aceptado'.format(numero)


def registrar(numero):
    logging.getLogger('pedidos').info(mensaje_de(numero))
    return mensaje_de(numero)
