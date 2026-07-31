"""Cliente de la API."""

import json

__version__ = "1.4.0"


def serializar(datos):
    return json.dumps(datos, sort_keys=True)
