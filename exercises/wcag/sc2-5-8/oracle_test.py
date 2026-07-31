"""Oraculo congelado: las acciones van a donde iban y dicen lo mismo.

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



class AccionesTest(unittest.TestCase):

    def test_las_acciones_siguen_yendo_a_donde_iban(self):
        self.assertEqual([e[1]['href'] for e in por_tag('a')], ['/editar', '/borrar'])

    def test_siguen_diciendo_lo_mismo(self):
        self.assertEqual([e[1]['title'] for e in por_tag('a')], ['Editar', 'Borrar'])

    def test_las_dos_siguen_declarando_su_medida(self):
        for e in por_tag('a'):
            self.assertIn('width', e[1].get('style', ''),
                          'borrar la medida no agranda nada: deja al instrumento sin que medir')


if __name__ == '__main__':
    unittest.main()
