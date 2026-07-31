"""Consumidor de trabajos."""

APAGANDO = []


def preparar():
    # Nadie avisa cuando el proceso se esta apagando.
    return None


def tomar(trabajos):
    return [t for t in trabajos if not APAGANDO]
