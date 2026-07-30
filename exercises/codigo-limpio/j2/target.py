"""Solucion J2: las constantes se citan por su nombre, no se heredan."""


class LimitesDeEvento:
    TOPE_DE_CUPOS = 100
    MINIMO_DE_CUPOS = 5


class ServicioEventos:
    def cupos_validos(self, cantidad):
        return (LimitesDeEvento.MINIMO_DE_CUPOS <= cantidad
                <= LimitesDeEvento.TOPE_DE_CUPOS)
