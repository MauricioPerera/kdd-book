"""Punto de partida del ejercicio G36. Viola la Ley de Demeter."""


class Direccion:
    def __init__(self, ciudad, pais, codigo_postal):
        self.ciudad = ciudad
        self.pais = pais
        self.codigo_postal = codigo_postal


class Cliente:
    def __init__(self, nombre, direccion):
        self.nombre = nombre
        self.direccion = direccion


class Pedido:
    def __init__(self, numero, cliente):
        self.numero = numero
        self.cliente = cliente


def etiqueta_envio(pedido):
    ciudad = pedido.cliente.direccion.ciudad
    pais = pedido.cliente.direccion.pais
    codigo = pedido.cliente.direccion.codigo_postal
    return '{}, {} ({})'.format(ciudad, pais, codigo)
