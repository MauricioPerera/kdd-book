"""Oraculo congelado: lo que la app arma no cambia.

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


class PayloadTest(unittest.TestCase):

    def test_el_payload_no_cambia(self):
        self.assertEqual(app.armar_payload(7, ['b', 'a']),
                         {'pedido': 7, 'items': ['a', 'b'], 'total': 2})

    def test_los_items_salen_ordenados(self):
        self.assertEqual(app.armar_payload(1, ['c', 'a', 'b'])['items'],
                         ['a', 'b', 'c'])


if __name__ == '__main__':
    unittest.main()
