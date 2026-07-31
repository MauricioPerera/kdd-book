"""Oraculo congelado: lo que el worker hace con la cola no cambia.

El oraculo prueba `plan` y NO llama a `arrancar`, que es la ruta de arranque.
La primera version si la llamaba, y estaba mal de dos maneras: en POSIX habria
forkeado de verdad durante la prueba, y en Windows `os.fork` no existe y el
oraculo se ponia rojo sobre el seed —lo detecto `test_exercises`, que compara
el oraculo contra el `kind` declarado—.

Que la ruta de arranque no se ejecute en ninguna prueba no es una excepcion de
este ejercicio: es lo normal. Y es exactamente por lo que hace falta un
instrumento que lea el codigo entero.

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


class WorkerTest(unittest.TestCase):

    def test_cada_pedido_queda_listo(self):
        self.assertEqual(app.procesar(3), {'pedido': 3, 'estado': 'listo'})

    def test_procesa_toda_la_cola_en_orden(self):
        self.assertEqual([r['pedido'] for r in app.plan([1, 2, 3])], [1, 2, 3])


if __name__ == '__main__':
    unittest.main()
