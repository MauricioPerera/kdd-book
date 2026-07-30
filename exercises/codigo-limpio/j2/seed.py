"""Punto de partida J2: se hereda solo para escribir las constantes cortas."""


class LimitesDeEvento:
    TOPE_DE_CUPOS = 100
    MINIMO_DE_CUPOS = 5


class ServicioEventos(LimitesDeEvento):
    def cupos_validos(self, cantidad):
        return self.MINIMO_DE_CUPOS <= cantidad <= self.TOPE_DE_CUPOS
