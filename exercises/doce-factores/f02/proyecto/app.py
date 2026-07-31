"""Cliente de la API de pedidos."""


def armar_payload(numero, items):
    return {'pedido': numero, 'items': sorted(items), 'total': len(items)}


def enviar(numero, items):
    # El cliente HTTP se importa aca adentro porque solo hace falta al enviar.
    # Que el import sea perezoso no lo saca del manifiesto: sigue siendo una
    # dependencia del proyecto.
    import peticiones
    return peticiones.post('/pedidos', armar_payload(numero, items))
