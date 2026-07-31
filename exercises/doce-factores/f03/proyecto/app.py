"""Cliente de alertas."""

import os

API_KEY = os.environ['API_KEY']


def cabeceras(destinatario):
    return {'Authorization': 'Bearer ' + API_KEY,
            'X-Destinatario': destinatario}
