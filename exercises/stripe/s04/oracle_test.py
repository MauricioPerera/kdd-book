"""Oraculo congelado: sigue siendo el mismo GET a customers, con el mismo nombre.
"""

import os
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))


def texto(ruta):
    with open(os.path.join(AQUI, ruta), encoding='utf-8') as fh:
        return fh.read()


class ClienteTest(unittest.TestCase):

    def test_sigue_siendo_un_get_a_customers(self):
        contenido = texto('proyecto/client.py')
        self.assertIn('requests.get(', contenido)
        self.assertIn('v1/customers/', contenido)

    def test_la_funcion_no_cambia_de_nombre(self):
        self.assertIn('def obtener_cliente(cliente_id):', texto('proyecto/client.py'))


if __name__ == '__main__':
    unittest.main()
