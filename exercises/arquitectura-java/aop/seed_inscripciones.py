"""Punto de partida: el negocio hace de todo, incluso registrar."""

import logging


def total_inscripcion(base, cantidad):
    logging.info('calculando total')
    total = base * cantidad
    logging.debug('total calculado')
    return total
