"""Punto de partida G7: la clase base nombra a una de sus variantes."""


class Notificacion:
    def __init__(self, destino):
        self.destino = destino

    def canal(self):
        return 'ninguno'

    def preferida(self):
        return Email(self.destino)


class Email(Notificacion):
    def canal(self):
        return 'email'
