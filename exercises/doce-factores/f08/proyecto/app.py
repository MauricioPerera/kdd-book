"""Worker de la cola de pedidos."""


def procesar(pedido):
    return {'pedido': pedido, 'estado': 'listo'}


def plan(cola):
    return [procesar(p) for p in cola]


def arrancar(cola):
    # En primer plano: de reiniciarlo y de recoger su salida se ocupa el gestor
    # de procesos del sistema, que para eso esta.
    return plan(cola)
