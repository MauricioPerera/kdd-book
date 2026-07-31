"""Cliente de la API."""

__version__ = "1.4.0"

import json


def serializar(datos):
    return json.dumps(datos, sort_keys=True)
