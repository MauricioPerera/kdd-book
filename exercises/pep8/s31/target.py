"""Entorno."""

import os

registro = os.environ


def tiene(clave):
    return clave in registro
