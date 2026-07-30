"""Punto de partida G25: numeros sin nombre en medio del calculo."""


def precio_con_recargo(base, dias_de_anticipacion):
    if dias_de_anticipacion < 15:
        return round(base * 1.35, 2)
    return round(base * 1.1, 2)
