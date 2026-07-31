"""Oraculo congelado: la configuracion de Vite sigue siendo una configuracion de Vite valida.
"""

import os
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))


def texto(ruta):
    with open(os.path.join(AQUI, ruta), encoding='utf-8') as fh:
        return fh.read()



class ConfigTest(unittest.TestCase):

    def test_sigue_siendo_una_configuracion_de_vite(self):
        contenido = texto('proyecto/vite.config.ts')
        self.assertIn("from 'vite'", contenido)
        self.assertIn('defineConfig(', contenido)

    def test_la_hoja_de_entrada_no_cambia(self):
        self.assertIn('@import "tailwindcss";', texto('proyecto/src/app.css'))


if __name__ == '__main__':
    unittest.main()
