"""Oraculo congelado: lo que la app responde no cambia.

Vive FUERA de `proyecto/` a proposito. `entorno_checks` mide todos los `.py` del
proyecto, asi que un oraculo adentro seria medido como si fuera codigo de la
app: en varias reglas eso alcanzaria para cambiar el resultado —un `bind` en el
oraculo pondria `puerto` en verde sin que nadie ate un puerto—.
"""

import os
import sys
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, 'proyecto'))


import app  # noqa: E402


class RespuestaTest(unittest.TestCase):

    def test_la_ruta_de_salud_responde_ok(self):
        self.assertEqual(app.responder('/salud'), (200, 'ok'))

    def test_una_ruta_desconocida_responde_404(self):
        self.assertEqual(app.responder('/otra'), (404, 'no esta'))


if __name__ == '__main__':
    unittest.main()
