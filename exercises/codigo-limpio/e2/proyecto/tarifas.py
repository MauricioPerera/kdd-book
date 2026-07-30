"""Funcionalidad del proyecto de ejemplo: calculo de tarifas de un evento."""

SEGUNDOS_POR_HORA = 3600


def precio_final(base, descuento_pct):
    """Precio con descuento, redondeado a dos decimales."""
    if descuento_pct < 0 or descuento_pct > 100:
        raise ValueError('descuento fuera de rango: {}'.format(descuento_pct))
    return round(base * (100 - descuento_pct) / 100, 2)


def cupos_disponibles(capacidad, inscriptos):
    """Cupos que quedan; nunca negativo."""
    return max(0, capacidad - inscriptos)


def duracion_en_horas(segundos):
    """Duracion en horas con un decimal."""
    return round(segundos / SEGUNDOS_POR_HORA, 1)
