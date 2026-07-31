"""Worker de la cola de pedidos."""

import os


def procesar(pedido):
    return {'pedido': pedido, 'estado': 'listo'}


def plan(cola):
    return [procesar(p) for p in cola]


def _desprenderse():
    os.fork()
    os.setsid()
    open('/var/run/worker.pid', 'w')


def arrancar(cola):
    _desprenderse()
    return plan(cola)
