"""Oraculo congelado: el despliegue de produccion sigue declarando lo mismo.

Aca el oraculo tiene una funcion concreta: el atajo para igualar dos
despliegues es **borrar el servicio que molesta**, y eso lo pone en rojo.

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

import re  # noqa: E402

PROD = os.path.join(AQUI, 'proyecto', 'prod.yml')


def texto():
    with open(PROD, encoding='utf-8') as fh:
        return fh.read()


class DespliegueTest(unittest.TestCase):

    def test_produccion_sigue_declarando_sus_dos_servicios(self):
        self.assertEqual(sorted(re.findall(r'^  (\w+):', texto(), re.M)),
                         ['cache', 'db'])

    def test_produccion_sigue_publicando_el_puerto(self):
        self.assertIn('"5432:5432"', texto())

    def test_la_cache_no_cambia(self):
        self.assertIn('image: redis:7', texto())


if __name__ == '__main__':
    unittest.main()
