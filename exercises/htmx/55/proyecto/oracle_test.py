"""Oraculo congelado: lo que la app devuelve no cambia.

Fija los dos cuerpos —la pagina entera y el fragmento— y no dice nada de las
cabeceras. Por eso pasa igual antes y despues: agregar `Vary` no cambia lo que
el servidor responde, cambia lo que la cache puede hacer con eso. Quien lo dice
es el instrumento.
"""

import unittest

from app import responder


class RespuestaTest(unittest.TestCase):

    def test_sin_la_cabecera_devuelve_la_pagina_entera(self):
        _estado, _cab, cuerpo = responder('/inscriptos', {})
        self.assertIn('<html>', cuerpo)
        self.assertIn('<table>', cuerpo)

    def test_con_la_cabecera_devuelve_solo_el_fragmento(self):
        _estado, _cab, cuerpo = responder('/inscriptos', {'HX-Request': 'true'})
        self.assertNotIn('<html>', cuerpo)
        self.assertTrue(cuerpo.startswith('<tbody'))

    def test_los_dos_traen_las_mismas_filas(self):
        _e1, _c1, entera = responder('/inscriptos', {})
        _e2, _c2, fragmento = responder('/inscriptos', {'HX-Request': 'true'})
        for nombre in ('Ana', 'Beto'):
            self.assertIn(nombre, entera)
            self.assertIn(nombre, fragmento)

    def test_el_estado_es_200(self):
        estado, _cab, _cuerpo = responder('/inscriptos', {})
        self.assertEqual(estado, 200)

    def test_sigue_siendo_html(self):
        _estado, cabeceras, _cuerpo = responder('/inscriptos', {})
        self.assertTrue(cabeceras['Content-Type'].startswith('text/html'))
