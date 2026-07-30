"""Calculo de cupos y tarifas del proyecto de ejemplo."""

TOPE_DE_CUPOS = 100


def cupos_libres(capacidad, inscriptos):
    """Cupos que quedan, sin pasar del tope y nunca negativo."""
    return max(0, min(capacidad, TOPE_DE_CUPOS) - inscriptos)


def precio_final(base, descuento_pct):
    """Precio con descuento, redondeado a dos decimales."""
    if descuento_pct < 0 or descuento_pct > 100:
        raise ValueError('descuento fuera de rango')
    return round(base * (100 - descuento_pct) / 100, 2)
