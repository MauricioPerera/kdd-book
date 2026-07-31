"""Oraculo congelado: la clave sigue resuelta en config.py y client.py no cambia.
"""

import os
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))


def texto(ruta):
    with open(os.path.join(AQUI, ruta), encoding='utf-8') as fh:
        return fh.read()


class ConfigTest(unittest.TestCase):

    def test_config_sigue_declarando_stripe_key(self):
        self.assertIn('STRIPE_KEY', texto('proyecto/config.py'))

    def test_el_cliente_no_cambia(self):
        contenido = texto('proyecto/client.py')
        self.assertIn('from config import STRIPE_KEY', contenido)
        self.assertIn('api.stripe.com/v1/customers', contenido)


if __name__ == '__main__':
    unittest.main()
