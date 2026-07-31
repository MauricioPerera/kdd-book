"""Oraculo congelado: con la misma configuracion, la app manda lo mismo.

El oraculo pone la clave en el entorno antes de importar, y por eso pasa igual
sobre el seed y sobre la solucion: **dada la misma configuracion, el
comportamiento es el mismo**. Lo que cambia no es que manda la app sino de
donde saca la clave, y eso ningun test lo ve.

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

os.environ.setdefault('API_KEY', 'sk-live-9f3a2b')

import app  # noqa: E402


class CabecerasTest(unittest.TestCase):

    def test_la_cabecera_de_autorizacion_no_cambia(self):
        self.assertEqual(app.cabeceras('ana')['Authorization'],
                         'Bearer sk-live-9f3a2b')

    def test_el_destinatario_sigue_viajando(self):
        self.assertEqual(app.cabeceras('ana')['X-Destinatario'], 'ana')


if __name__ == '__main__':
    unittest.main()
