"""Oraculo congelado: lo que la pagina muestra no cambia.

Para una pagina, el comportamiento observable es su contenido: que elementos
tiene, que dice cada uno, a donde apunta. Este oraculo fija eso y no sabe nada
de la tecnica — pasa igual antes y despues, como en cualquier refactorizacion.
Quien dice si la tecnica se aplico es el instrumento.

**No importa el instrumento a proposito.** Parsea con `html.parser` por su
cuenta aunque `html_checks` ya tenga un parser, porque un oraculo que usa el
parser del instrumento le da la razon por construccion: si el parser se
equivoca, los dos se equivocan igual y nadie lo nota.
"""

import html.parser
import os
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))


class _Lector(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.elementos = []

    def handle_starttag(self, tag, attrs):
        self.elementos.append((tag, dict(attrs)))

    handle_startendtag = handle_starttag


def elementos():
    lector = _Lector()
    with open(os.path.join(AQUI, 'target.html'), encoding='utf-8') as fh:
        lector.feed(fh.read())
    return lector.elementos


class PaginaTest(unittest.TestCase):

    def _por_tag(self, tag):
        return [a for t, a in elementos() if t == tag]

    def test_el_boton_sigue_pidiendo_el_reporte(self):
        botones = self._por_tag('button')
        self.assertEqual(len(botones), 1)
        self.assertEqual(botones[0].get('hx-get'), '/reporte')

    def test_el_destino_no_cambia(self):
        self.assertEqual(self._por_tag('button')[0].get('hx-target'), '#salida')

    def test_la_salida_sigue_existiendo(self):
        self.assertEqual(len([d for d in self._por_tag('div')
                              if d.get('id') == 'salida']), 1)

    def test_el_panel_conserva_su_id(self):
        self.assertEqual(len([d for d in self._por_tag('div')
                              if d.get('id') == 'panel']), 1)


if __name__ == '__main__':
    unittest.main()
