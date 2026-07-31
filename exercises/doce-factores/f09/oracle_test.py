"""Oraculo congelado: lo que el consumidor hace con los trabajos no cambia.

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


class ConsumidorTest(unittest.TestCase):

    def test_toma_los_trabajos_mientras_no_se_apaga(self):
        app.APAGANDO.clear()
        self.assertEqual(app.tomar([1, 2, 3]), [1, 2, 3])

    def test_deja_de_tomar_cuando_se_esta_apagando(self):
        app.APAGANDO.clear()
        app.APAGANDO.append(True)
        self.assertEqual(app.tomar([1, 2, 3]), [])
        app.APAGANDO.clear()

    def test_preparar_no_rompe(self):
        self.assertIsNone(app.preparar())


if __name__ == '__main__':
    unittest.main()
