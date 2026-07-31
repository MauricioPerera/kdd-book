"""Consumidor de trabajos."""

import signal

APAGANDO = []


def _apagar(_numero, _marco):
    # Dejar de tomar trabajos nuevos. Los que estan en curso terminan.
    APAGANDO.append(True)


def preparar():
    signal.signal(signal.SIGTERM, _apagar)


def tomar(trabajos):
    return [t for t in trabajos if not APAGANDO]
