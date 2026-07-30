"""Solucion de referencia del ejercicio G36: cada objeto sabe de su vecino
inmediato y nadie navega el mapa completo del sistema."""


class Direccion:
    def __init__(self, ciudad, pais, codigo_postal):
        self.ciudad = ciudad
        self.pais = pais
        self.codigo_postal = codigo_postal

    def etiqueta(self):
        return '{}, {} ({})'.format(self.ciudad, self.pais, self.codigo_postal)


class Cliente:
    def __init__(self, nombre, direccion):
        self.nombre = nombre
        self.direccion = direccion

    def etiqueta_destino(self):
        return self.direccion.etiqueta()


class Pedido:
    def __init__(self, numero, cliente):
        self.numero = numero
        self.cliente = cliente

    def etiqueta_destino(self):
        return self.cliente.etiqueta_destino()


def etiqueta_envio(pedido):
    return pedido.etiqueta_destino()
