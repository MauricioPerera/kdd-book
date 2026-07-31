"""Oraculo congelado: lo que la plantilla renderiza no cambia.

Para una plantilla, el comportamiento observable es su salida: que entradas
aparecen, en que orden, con que dato en cada lugar. Este oraculo fija eso
renderizando con datos benignos y no sabe nada de la tecnica.

**Y con datos benignos la salida es IDENTICA antes y despues.** No es un
descuido del oraculo: es lo que hace falta entender del escapado. `{{{autor}}}`
y `{{autor}}` producen exactamente lo mismo mientras nadie escriba un `<`. La
diferencia aparece solo con contenido hostil, o sea justo con el caso que
ninguna prueba escrita con datos de ejemplo va a cubrir. Por eso la regla 1 de
htmx necesita un instrumento y no le alcanza con tests.

No mira el encabezado del archivo: el seed trae un comentario distinto y fijar
el texto de un comentario seria fijar prosa, no comportamiento.
"""

import os
import re
import unittest

from render import render

AQUI = os.path.dirname(os.path.abspath(__file__))

DATOS = {
    'comentarios': [
        {'autor': 'Ana', 'texto': 'Muy claro, gracias'},
        {'autor': 'Bruno', 'texto': 'Lo probe y anda'},
    ],
    'total': 2,
}


def salida():
    with open(os.path.join(AQUI, 'plantilla.mustache'), encoding='utf-8') as fh:
        return render(fh.read(), DATOS)


class FragmentoTest(unittest.TestCase):

    def test_renderiza_una_entrada_por_comentario(self):
        self.assertEqual(len(re.findall(r'<li class="comentario">', salida())), 2)

    def test_cada_entrada_muestra_su_autor(self):
        self.assertEqual(re.findall(r'<b class="autor">(.*?)</b>', salida()),
                         ['Ana', 'Bruno'])

    def test_cada_entrada_muestra_su_texto(self):
        self.assertEqual(re.findall(r'<p class="texto">(.*?)</p>', salida()),
                         ['Muy claro, gracias', 'Lo probe y anda'])

    def test_el_contenedor_conserva_el_id_que_htmx_reemplaza(self):
        self.assertIn('<ul id="comentarios">', salida())

    def test_el_pie_sigue_contando(self):
        self.assertIn('2 comentario(s)', salida())


if __name__ == '__main__':
    unittest.main()
