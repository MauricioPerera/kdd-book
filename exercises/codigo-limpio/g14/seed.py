"""Punto de partida G14: Liquidacion vive metida en los datos de Empleado."""


class Empleado:
    def __init__(self, tarifa, horas, extra):
        self.tarifa = tarifa
        self.horas = horas
        self.extra = extra


class Liquidacion:
    def pago(self, empleado):
        tarifa = empleado.tarifa
        horas = empleado.horas
        extra = empleado.extra
        return tarifa * horas + extra


def liquidar(empleado):
    return Liquidacion().pago(empleado)
