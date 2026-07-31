"""Entorno."""

import os

RegistroGlobal = os.environ


def tiene(clave):
    return clave in RegistroGlobal
