"""Errores del dominio."""


class SaldoInsuficiente(ValueError):
    """El saldo no alcanza para la operacion."""


def girar(saldo, monto):
    if monto > saldo:
        raise SaldoInsuficiente(monto)
    return saldo - monto
