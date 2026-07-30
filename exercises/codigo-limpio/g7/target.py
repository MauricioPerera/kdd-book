"""Solucion G7: la base ya no nombra a ninguna variante.

El canal preferido se configura a nivel de modulo, despues de declarar las
clases. La base sigue delegando, pero no sabe en quien.
"""


class Notificacion:
    def __init__(self, destino):
        self.destino = destino

    def canal(self):
        return 'ninguno'

    def preferida(self):
        return CANAL_PREFERIDO(self.destino)


class Email(Notificacion):
    def canal(self):
        return 'email'


CANAL_PREFERIDO = Email
