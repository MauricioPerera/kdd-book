"""Oraculo congelado: el proyecto sigue llamandose igual y declarando la misma version de Tailwind.
"""

import os
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))


def texto(ruta):
    with open(os.path.join(AQUI, ruta), encoding='utf-8') as fh:
        return fh.read()



import json


class ManifiestoTest(unittest.TestCase):

    def test_el_proyecto_no_cambia_de_nombre_ni_de_version(self):
        datos = json.loads(texto('proyecto/package.json'))
        self.assertEqual(datos['name'], 'demo')
        self.assertEqual(datos['dependencies']['tailwindcss'], '^4.0.0')


if __name__ == '__main__':
    unittest.main()
