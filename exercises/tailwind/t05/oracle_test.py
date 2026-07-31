"""Oraculo congelado: el componente sigue mostrando el mismo mensaje.
"""

import os
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))


def texto(ruta):
    with open(os.path.join(AQUI, ruta), encoding='utf-8') as fh:
        return fh.read()



class ComponenteTest(unittest.TestCase):

    def test_el_componente_sigue_mostrando_lo_mismo(self):
        contenido = texto('proyecto/Alert.vue')
        self.assertIn("const message = 'Alerta'", contenido)
        self.assertIn('class="rounded-lg p-4"', contenido)


if __name__ == '__main__':
    unittest.main()
