"""Cuentas."""


class cuenta_corriente:
    """Una cuenta corriente."""

    def __init__(self, saldo):
        self.saldo = saldo

    def girar(self, monto):
        self.saldo -= monto
        return self.saldo
