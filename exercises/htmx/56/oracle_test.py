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

    def test_el_enlace_sigue_apuntando_a_pedidos(self):
        enlaces = self._por_tag('a')
        self.assertEqual(len(enlaces), 1)
        self.assertEqual(enlaces[0].get('href'), '/pedidos')

    def test_el_boost_sigue_activo(self):
        self.assertEqual(self._por_tag('body')[0].get('hx-boost'), 'true')

    def test_la_zona_conserva_su_id(self):
        self.assertEqual(len([m for m in self._por_tag('main')
                              if m.get('id') == 'zona']), 1)

    def test_el_token_sigue_siendo_el_mismo(self):
        portadores = [a for _t, a in elementos()
                      if 'X-CSRF-TOKEN' in (a.get('hx-headers') or '')]
        self.assertEqual(len(portadores), 1)
        self.assertIn('abc123', portadores[0]['hx-headers'])


if __name__ == '__main__':
    unittest.main()
