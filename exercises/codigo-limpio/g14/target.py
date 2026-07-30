"""Solucion G14: el que tiene los datos hace la cuenta."""


class Empleado:
    def __init__(self, tarifa, horas, extra):
        self.tarifa = tarifa
        self.horas = horas
        self.extra = extra

    def pago(self):
        return self.tarifa * self.horas + self.extra


class Liquidacion:
    def pago(self, empleado):
        return empleado.pago()


def liquidar(empleado):
    return Liquidacion().pago(empleado)
