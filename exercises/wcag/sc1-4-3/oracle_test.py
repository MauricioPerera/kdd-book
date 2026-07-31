"""Oraculo congelado: la pagina dice lo mismo.

El oraculo no mira los colores a proposito: **el color es justamente lo que
cambia**. Lo que si comprueba es que los dos elementos sigan declarando uno,
porque borrar el estilo no arregla el contraste — deja al instrumento sin nada
que medir, que es exit 2 y no verde.

**No importa el instrumento.** Parsea con `html.parser` por su cuenta aunque
`a11y_checks` y `html_checks` ya tengan un arbol, porque un oraculo que usa el
parser del instrumento le da la razon por construccion: si el parser se
equivoca, los dos se equivocan igual y nadie lo nota.
"""

import html.parser
import os
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))

VACIOS = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link',
          'meta', 'param', 'source', 'track', 'wbr'}


class _Lector(html.parser.HTMLParser):

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.elementos = []
        self.pila = []
        self.texto = []
        self.mudo = 0

    def handle_starttag(self, tag, attrs):
        registro = [tag, dict(attrs), '']
        self.elementos.append(registro)
        if tag in ('script', 'style'):
            self.mudo += 1
        if tag not in VACIOS:
            self.pila.append(registro)

    def handle_startendtag(self, tag, attrs):
        self.elementos.append([tag, dict(attrs), ''])

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.mudo = max(0, self.mudo - 1)
        if tag in VACIOS:
            return
        while self.pila and self.pila[-1][0] != tag:
            self.pila.pop()
        if self.pila:
            self.pila.pop()

    def handle_data(self, data):
        if not data.strip():
            return
        if self.pila:
            self.pila[-1][2] += ' ' + data.strip()
        if not self.mudo:
            self.texto.append(data.strip())


def _leer():
    lector = _Lector()
    with open(os.path.join(AQUI, 'target.html'), encoding='utf-8') as fh:
        lector.feed(fh.read())
    return lector


def elementos():
    return _leer().elementos


def por_tag(tag):
    return [e for e in elementos() if e[0] == tag]


def texto_de_la_pagina():
    return ' '.join(_leer().texto)


def crudo():
    with open(os.path.join(AQUI, 'target.html'), encoding='utf-8') as fh:
        return fh.read()



class TerminosTest(unittest.TestCase):

    def test_el_texto_no_cambia(self):
        self.assertIn('Terminos', texto_de_la_pagina())
        self.assertIn('El servicio se presta tal cual esta.', texto_de_la_pagina())

    def test_la_estructura_no_cambia(self):
        self.assertEqual([e[0] for e in elementos()], ['article', 'h1', 'p'])

    def test_los_dos_siguen_declarando_su_color(self):
        for e in elementos()[1:]:
            self.assertIn('color', e[1].get('style', ''),
                          'borrar el estilo no arregla el contraste, lo esconde')


if __name__ == '__main__':
    unittest.main()
