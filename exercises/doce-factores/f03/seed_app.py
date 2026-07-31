"""Cliente de alertas."""

import os

API_KEY = 'sk-live-9f3a2b'


def cabeceras(destinatario):
    return {'Authorization': 'Bearer ' + API_KEY,
            'X-Destinatario': destinatario}
