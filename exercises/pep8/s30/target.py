"""Errores del dominio."""


class SaldoInsuficienteError(ValueError):
    """El saldo no alcanza para la operacion."""


def girar(saldo, monto):
    if monto > saldo:
        raise SaldoInsuficienteError(monto)
    return saldo - monto
