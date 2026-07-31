"""Oraculo congelado: con la misma config, la app habla con el mismo servicio.

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

os.environ.setdefault('DATABASE_URL', 'postgres://app@db.interno:5432/tienda')

import app  # noqa: E402


class AlmacenTest(unittest.TestCase):

    def test_la_descripcion_no_cambia(self):
        self.assertEqual(app.describir(), 'pedidos via postgres')

    def test_el_destino_sigue_siendo_el_mismo(self):
        self.assertTrue(app.DESTINO.endswith('/tienda'))


if __name__ == '__main__':
    unittest.main()
