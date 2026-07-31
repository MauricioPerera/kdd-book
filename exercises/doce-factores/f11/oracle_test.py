"""Oraculo congelado: lo que la app registra no cambia.

El oraculo fija el mensaje y el formato, que son el comportamiento, y no toca
el destino, que es la tecnica. No llama a `configurar()` a proposito: sobre el
seed eso crearia el logfile, y una prueba que produce el defecto que mide no
sirve para medirlo.

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


class RegistroTest(unittest.TestCase):

    def test_el_mensaje_no_cambia(self):
        self.assertEqual(app.mensaje_de(7), 'pedido 7 aceptado')

    def test_el_formato_no_cambia(self):
        self.assertEqual(app.FORMATO, '%(levelname)s %(name)s %(message)s')

    def test_registrar_devuelve_lo_que_registro(self):
        self.assertEqual(app.registrar(7), 'pedido 7 aceptado')


if __name__ == '__main__':
    unittest.main()
