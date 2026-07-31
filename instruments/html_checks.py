#!/usr/bin/env python3
"""Instrumentos que miden sobre HTML (documentacion de htmx).

Familia nueva por una razon concreta: las otras cinco parsean AST de Python o
corren comandos, y **ninguna sirve para una fuente sobre hipermedia**. El
triaje de la documentacion de htmx dio 6 tecnicas medibles y las seis leen
HTML, HTTP o plantillas. El metodo transferia; los instrumentos no.

Cubre las tres que leen HTML:

    progresivo  el elemento que emite request funciona sin javascript
    csrf        el token viaja en un elemento que de verdad lo lleva
    indicador   quien emite request da senal de que algo esta pasando

Solo stdlib. `html.parser` no devuelve un arbol, asi que se construye uno
rastreando la anidacion: las tres reglas preguntan por **ancestros** —"el
indicador esta en alcance", "el token esta arriba"— y sin arbol ninguna se
puede escribir.

Exit codes (convencion KDD):
  0  la propiedad se cumple
  1  no se cumple
  2  no se pudo verificar (HTML ilegible, o falta la declaracion que hace falta)

Uso:
    python html_checks.py --rule progresivo <archivo.html> [...]
    python html_checks.py --list
"""

__all__ = [
    'Elemento',
    'NoVerificable',
    'check_csrf',
    'check_indicador',
    'check_progresivo',
    'main',
    'parsear',
]

import argparse
import html.parser
import os
import sys

# Sobre que mide esta familia: una pagina HTML.
#
# Lo declara cada familia y no una lista en `memoria.py`, porque esa lista
# ya quedo vieja dos veces. `aplicar` elige por este campo que instrumentos
# puede correr sobre lo que le dieron; sin el, agregar una familia la deja
# afuera en silencio y nada falla.
ARTEFACTO = 'html'


# Atributos que hacen que un elemento emita una peticion.
VERBOS = ('hx-get', 'hx-post', 'hx-put', 'hx-patch', 'hx-delete')

# Elementos sin cierre: si se apilaran, se llevarian puesto todo el arbol.
VACIOS = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link',
          'meta', 'param', 'source', 'track', 'wbr'}


class NoVerificable(Exception):
    """Falta el dato sin el cual la regla no se puede evaluar (exit 2)."""


class Elemento:
    """Un elemento del documento, con su lugar en el arbol y su texto
    propio.
    """
    __slots__ = ('tag', 'attrs', 'padre', 'hijos', 'linea', 'texto')

    def __init__(self, tag, attrs, padre, linea):
        self.tag = tag
        self.attrs = attrs
        self.padre = padre
        self.hijos = []
        self.linea = linea
        # Texto propio, sin el de los descendientes. Lo agrego `a11y_checks`,
        # que necesita comparar la etiqueta VISIBLE de un control contra su
        # nombre accesible; las tres reglas de este modulo solo miran atributos.
        # Vive aca y no en un arbol aparte porque dos parsers de HTML en el
        # mismo repositorio terminan discrepando, y ya paso una vez con la
        # definicion de emisor.
        self.texto = ''

    def ancestros(self):
        """Los ancestros, del padre hacia la raiz."""
        actual = self.padre
        while actual is not None:
            yield actual
            actual = actual.padre

    def descendientes(self):
        """Los descendientes, en profundidad."""
        for hijo in self.hijos:
            yield hijo
            for nieto in hijo.descendientes():
                yield nieto

    def emite_request(self):
        """True si el elemento lleva un verbo htmx propio."""
        return any(v in self.attrs for v in VERBOS)

    def clases(self):
        """Las clases CSS declaradas, ya separadas."""
        return (self.attrs.get('class') or '').split()

    def texto_visible(self):
        """El texto propio mas el de los descendientes, normalizado.

        Se saltea `script` y `style`, cuyo contenido no lo ve nadie: contarlo
        haria que un boton con un `<script>` adentro pareciera tener etiqueta.
        """
        if self.tag in ('script', 'style'):
            return ''
        partes = [self.texto]
        partes.extend(h.texto_visible() for h in self.hijos)
        return ' '.join(' '.join(partes).split())

    def __repr__(self):
        return '<{}>'.format(self.tag)


class _Arbol(html.parser.HTMLParser):
    """Construye el arbol de elementos preservando la anidacion."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.raiz = Elemento('#document', {}, None, 0)
        self.actual = self.raiz
        self.todos = []

    def handle_starttag(self, tag, attrs):
        """Abre un elemento y lo cuelga de su padre."""
        nodo = Elemento(tag, {k: (v if v is not None else '') for k, v in attrs},
                        self.actual, self.getpos()[0])
        self.actual.hijos.append(nodo)
        self.todos.append(nodo)
        if tag not in VACIOS:
            self.actual = nodo

    def handle_startendtag(self, tag, attrs):
        """Un elemento que abre y cierra en la misma etiqueta."""
        nodo = Elemento(tag, {k: (v if v is not None else '') for k, v in attrs},
                        self.actual, self.getpos()[0])
        self.actual.hijos.append(nodo)
        self.todos.append(nodo)

    def handle_data(self, data):
        """Acumula el texto propio del elemento abierto."""
        if data.strip():
            self.actual.texto += ' ' + data

    def handle_endtag(self, tag):
        """Cierra hasta la etiqueta que corresponde, tolerando lo que quedo
        sin cerrar.
        """
        if tag in VACIOS:
            return
        nodo = self.actual
        while nodo is not self.raiz and nodo.tag != tag:
            nodo = nodo.padre
        if nodo is not self.raiz:
            self.actual = nodo.padre


def parsear(ruta):
    """Los elementos de una pagina, en el orden en que aparecen."""
    with open(ruta, 'r', encoding='utf-8') as fh:
        contenido = fh.read()
    arbol = _Arbol()
    try:
        arbol.feed(contenido)
    # html.parser es tolerante: si igual falla, no hay arbol y no se mide.
    except Exception as exc:
        raise NoVerificable('no se pudo parsear {}: {}'.format(ruta, exc))
    return arbol.todos


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def _emite(elemento):
    """True si el elemento termina emitiendo una peticion htmx.

    Cuenta el verbo propio y tambien `hx-boost` heredado: boost se hereda a los
    descendientes, asi que un `<a>` dentro de un `<body hx-boost>` emite igual.
    Vive en una funcion sola porque tenerlo duplicado ya hizo que dos reglas
    discreparan sobre que es un emisor.
    """
    if elemento.emite_request():
        return True
    if elemento.tag not in ('a', 'form'):
        return False
    return any('hx-boost' in n.attrs
               for n in [elemento] + list(elemento.ancestros()))


def _degrada(elemento):
    """True si el elemento sigue funcionando con javascript deshabilitado.

    Vale por si mismo si es un ancla con destino o un formulario con accion, y
    vale tambien si esta dentro de uno: la documentacion muestra justamente eso
    —envolver el input mejorado en un `<form action method>`— como la forma de
    hacer progresiva una pieza que no lo era.
    """
    candidatos = [elemento] + list(elemento.ancestros())
    for nodo in candidatos:
        if nodo.tag == 'a' and nodo.attrs.get('href'):
            return True
        if nodo.tag == 'form' and nodo.attrs.get('action'):
            return True
    return False


def check_progresivo(elementos, opts):
    """Mejora progresiva: quien emite request funciona sin javascript.

    La documentacion lo define de forma comprobable: hx-boost "degrada
    gracefully si javascript no esta habilitado: los enlaces y formularios
    siguen funcionando". Un `<button hx-get>` suelto no degrada; el mismo
    boton dentro de un `<form action>` si.
    """
    out = []
    for e in elementos:
        if not _emite(e):
            continue
        if _degrada(e):
            continue
        out.append((e.linea, '<{}> emite una peticion y no degrada sin javascript: '
                             'no es un <a href> ni un <form action>, ni esta dentro '
                             'de uno'.format(e.tag)))
    return out


def check_csrf(elementos, opts):
    """El token CSRF viaja en un elemento que de verdad lo lleva.

    Ademas del caso obvio —nadie declara el token— cubre la trampa que la
    propia documentacion senala: `hx-boost` no actualiza `<html>` ni `<body>`,
    asi que poner el token solo ahi lo deja viejo despues del primer swap.
    """
    if not opts.token:
        raise NoVerificable(
            'hay que declarar el nombre del header con --token (por ejemplo '
            'X-CSRF-TOKEN): adivinarlo seria inventar la convencion')
    emisores = [e for e in elementos if _emite(e)]
    if not emisores:
        raise NoVerificable('no hay ningun elemento que emita peticiones: '
                            'no hay nada cuyo token verificar')

    hay_boost = any('hx-boost' in e.attrs for e in elementos)
    out = []
    for e in emisores:
        portadores = [n for n in [e] + list(e.ancestros())
                      if opts.token in (n.attrs.get('hx-headers') or '')]
        oculto = any(h.tag == 'input' and h.attrs.get('type') == 'hidden'
                     and opts.token.lower() in (h.attrs.get('name') or '').lower()
                     for n in [e] + list(e.ancestros()) for h in n.descendientes())
        if not portadores and not oculto:
            out.append((e.linea, '<{}> emite una peticion sin el token {}: no hay '
                                 'hx-headers que lo lleve ni input oculto'
                        .format(e.tag, opts.token)))
        elif hay_boost and portadores and all(p.tag in ('html', 'body') for p in portadores):
            out.append((e.linea, '<{}> lleva el token solo en <{}>, y con hx-boost '
                                 'ese elemento no se actualiza: el token queda viejo '
                                 'tras el primer swap'
                        .format(e.tag, portadores[0].tag)))
    return out


def check_indicador(elementos, opts):
    """Quien emite una peticion da senal de que algo esta pasando.

    Sirve `hx-indicator` en el elemento o en un ancestro, o un descendiente con
    la clase `htmx-indicator`, que es el mecanismo por defecto.
    """
    out = []
    for e in elementos:
        if not e.emite_request():
            continue
        declarado = any('hx-indicator' in n.attrs for n in [e] + list(e.ancestros()))
        propio = any('htmx-indicator' in d.clases() for d in e.descendientes())
        if not declarado and not propio:
            out.append((e.linea, '<{}> emite una peticion sin indicador: ni '
                                 'hx-indicator en alcance ni un descendiente con '
                                 'la clase htmx-indicator'.format(e.tag)))
    return out


RULES = {
    'csrf': (check_csrf, 'CSRF: el token viaja en un elemento que de verdad lo lleva'),
    'indicador': (check_indicador, 'Indicador: quien emite request da senal'),
    'progresivo': (check_progresivo, 'Mejora progresiva: funciona sin javascript'),
}


def main(argv=None):
    """Corre la regla pedida sobre los archivos dados y devuelve el exit
    code.
    """
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--rule')
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--token', help='nombre del header CSRF, p.ej. X-CSRF-TOKEN')
    parser.add_argument('files', nargs='*')
    args = parser.parse_args(argv)

    if args.list:
        for nombre in sorted(RULES):
            print('{:11} {}'.format(nombre, RULES[nombre][1]))
        return 0

    if args.rule not in RULES:
        print('NO-VERIFICABLE: regla desconocida: {!r} (ver --list)'.format(args.rule))
        return 2
    if not args.files:
        print('NO-VERIFICABLE: no se indicaron archivos')
        return 2

    func, etiqueta = RULES[args.rule]
    violaciones = []
    for ruta in args.files:
        if not os.path.isfile(ruta):
            print('NO-VERIFICABLE: no existe {}'.format(ruta))
            return 2
        try:
            for linea, detalle in func(parsear(ruta), args):
                violaciones.append((ruta, linea, detalle))
        except NoVerificable as exc:
            print('NO-VERIFICABLE: {}: {}'.format(etiqueta, exc))
            return 2
        except OSError as exc:
            print('NO-VERIFICABLE: {}: {}'.format(etiqueta, exc))
            return 2

    if violaciones:
        print('INSTRUMENTO ROJO: {}'.format(etiqueta))
        for ruta, linea, detalle in violaciones:
            print('  {}:{}: {}'.format(os.path.basename(ruta), linea, detalle))
        return 1

    print('OK: {}'.format(etiqueta))
    return 0


if __name__ == '__main__':
    sys.exit(main())
