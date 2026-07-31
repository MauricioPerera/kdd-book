#!/usr/bin/env python3
"""Construye books/htmx.json a partir de los titulos de la documentacion.

Cuarto libro del grafo, y el primero que no es un libro: es la documentacion de
htmx (htmx.org/docs). Se agrega para probar hasta donde llega el metodo.

**Advertencia de corpus, la mas fuerte de las cuatro fuentes.** Codigo Limpio
aporta un catalogo enumerado por el autor y Scrum y XP los marcadores del PDF.
Esto es **documentacion de referencia**: describe una API, no cataloga tecnicas.
Sus 59 items son los titulos de seccion, extraidos del PDF por tamano de fuente
—no habia marcadores ni codigos— y agrupados por geometria. Es corpus del autor,
si, pero de un documento cuyo proposito no es enumerar tecnicas.

Eso se ve en el resultado: **46% cae en pila C** (instalacion, npm, webpack,
referencia de cabeceras, crear extensiones). No es que htmx hable de personas
como Scrum: habla de codigo. Cae bajo porque describir una API no es prescribir
una tecnica.

Y las medibles se concentran donde la documentacion **deja de describir y
empieza a prescribir**: Caching 1/1, Security 3/5, Boosting 1/2, y 0% en
instalacion, historial, extensiones, eventos, debugging y scripting.

El hallazgo que dejo esta fuente: **el metodo transfiere y los instrumentos no.**
Sus seis tecnicas medibles leen HTML, HTTP o plantillas, y ninguna de las 39
reglas que habia servia — todas parsean AST de Python. De ahi salieron
`html_checks` y `http_checks`.

Entrada: el volcado de titulos, una linea por entrada:

    <indice>| H<nivel> | p<pagina> | <titulo>

Uso:
    python build_htmx.py [books/htmx-toc.txt] [-o books/htmx.json]
"""

import argparse
import json
import os
import re
import sys

CL = 'codigo-limpio'
AJ = 'arquitectura-java'

# Secciones, para medir la fraccion medible de cada una por separado.
# (primer_indice, ultimo_indice, nombre)
SECCIONES = [
    (1, 2, 'introduccion'),
    (3, 7, 'instalacion'),
    (8, 17, 'ajax'),
    (18, 18, 'herencia de atributos'),
    (19, 20, 'boosting'),
    (21, 21, 'websockets y sse'),
    (22, 25, 'historial'),
    (26, 31, 'peticiones y respuestas'),
    (32, 33, 'validacion'),
    (34, 34, 'animaciones'),
    (35, 39, 'extensiones'),
    (40, 45, 'eventos y logging'),
    (46, 47, 'debugging'),
    (48, 50, 'scripting'),
    (51, 51, 'caching'),
    (52, 56, 'seguridad'),
    (57, 59, 'cierre'),
]

# Pila A: (instrumento, umbral). Las seis son `instrumented` — leen HTML, HTTP
# o plantillas, o sea el artefacto del que trata la tecnica. Ninguna depende de
# un registro que llene una persona.
A_NODES = {
    10: ('html_checks.py --rule indicador',
         'todo emisor de peticion con indicador en alcance'),
    20: ('html_checks.py --rule progresivo',
         'todo emisor funciona sin javascript'),
    51: ('http_checks.py --rule vary',
         'Vary: HX-Request cuando la respuesta varia por esa cabecera'),
    53: ('plantillas: interpolacion sin escapar (sin implementar: el marcador '
         'depende del motor y el proyecto tendria que declararlo)',
         'cero interpolaciones sin escapar'),
    55: ('http_checks.py --rule csp',
         'politica presente con las directivas declaradas'),
    56: ('html_checks.py --rule csrf',
         'el token viaja en un elemento que de verdad lo lleva'),
}

# Pila B: tecnica real cuya propiedad definitoria no es medible.
B_NODES = {9, 11, 12, 13, 15, 16, 17, 18, 19, 22, 23, 24, 25, 27, 28, 32,
           41, 42, 43, 45, 46, 48, 49, 50, 54}

ALIAS = {
    9: ['hx-trigger', 'triggering requests'],
    10: ['indicador de carga', 'request indicator', 'loading indicator'],
    11: ['hx-target', 'targeting'],
    12: ['hx-swap', 'swapping'],
    13: ['hx-sync', 'request synchronization'],
    15: ['out of band swap', 'hx-swap-oob'],
    16: ['hx-params', 'request parameters'],
    17: ['hx-confirm', 'confirmation'],
    18: ['herencia de atributos', 'attribute inheritance', 'hx-disinherit'],
    19: ['hx-boost', 'boosting'],
    20: ['mejora progresiva', 'progressive enhancement', 'graceful degradation'],
    22: ['soporte de historial', 'history support', 'hx-push-url'],
    27: ['manejo de respuestas', 'response handling'],
    28: ['CORS', 'cross origin'],
    32: ['validacion', 'validation'],
    41: ['inicializar biblioteca de terceros', 'third party init'],
    45: ['logging'],
    46: ['debugging'],
    48: ['scripting', 'hyperscript'],
    49: ['hx-on', 'inline handlers'],
    50: ['javascript de terceros', 'third party javascript'],
    51: ['cacheo', 'caching', 'Vary'],
    53: ['escapar contenido del usuario', 'escape user content', 'XSS'],
    54: ['hx-disable', 'security tools'],
    55: ['CSP', 'content security policy'],
    56: ['CSRF', 'cross site request forgery'],
}

WHY_NOT = {
    12: ('elegir la estrategia de swap correcta es un juicio sobre la interfaz, '
         'no un umbral'),
    18: 'que atributo conviene heredar y cual cortar depende del diseno de la pagina',
    19: 'usar hx-boost o no es una decision de arquitectura, no una propiedad medible',
    54: ('las herramientas existen y son medibles una por una; que combinacion hace '
         'falta es juicio'),
}

# Enlaces cruzados: pocos, y a proposito. Las otras tres fuentes hablan de codigo
# en el mismo lenguaje y por eso se cruzan mucho; esta habla de hipermedia y HTTP.
# Inventar vecindades para inflar el grafo seria lo contrario de lo que el grafo
# esta para hacer.
LINKS = {
    18: ['{}/g35'.format(CL)],   # datos configurables en los niveles superiores
    35: ['{}/11'.format(AJ)],    # OCP: extender sin modificar
    39: [35],
    51: [55],
    52: [53, 54, 55, 56],
    55: [56],
}

NOTA_CRUZADA = {
    18: ('La herencia de atributos de htmx es la misma idea que G35 de Codigo '
         'Limpio ("mantener los datos configurables en los niveles superiores"): '
         'declarar arriba y heredar hacia abajo. Martin la deja en pila B porque '
         'que dato conviene subir es un juicio, y aca pasa lo mismo con que '
         'atributo conviene heredar.'),
    35: ('El mecanismo de extensiones es OCP aplicado: se agrega comportamiento '
         'sin tocar el nucleo. Caules lo deja medible porque lo operacionaliza '
         'como "agregar una funcionalidad no debe obligar a tocar el '
         'controlador"; htmx describe el mecanismo pero no da con que medirlo.'),
    53: ('Es la unica de las seis medibles que todavia no tiene instrumento. Lee '
         'plantillas, y el marcador de interpolacion sin escapar cambia con cada '
         'motor, asi que el proyecto tendria que declarar cual usa — igual que '
         'declara sus capas para `arch_checks`.'),
}

_LINEA = re.compile(r'^\s*(\d+)\|\s*H(\d)\s*\|\s*p(\d+)\s*\|\s*(.+?)\s*$')


def leer(texto):
    out = {}
    for linea in texto.splitlines():
        m = _LINEA.match(linea)
        if m:
            out[int(m.group(1))] = (int(m.group(2)), int(m.group(3)), m.group(4))
    return out


def seccion_de(indice):
    for desde, hasta, nombre in SECCIONES:
        if desde <= indice <= hasta:
            return nombre
    return 'sin seccion'


def build(texto):
    entradas = leer(texto)
    faltan = [i for i in list(A_NODES) + sorted(B_NODES) if i not in entradas]
    if faltan:
        raise SystemExit('ERROR: indices del triaje que no existen: {}'.format(faltan))

    ids = {i: '{:02d}'.format(i) for i in entradas}

    def destino(t):
        return t if isinstance(t, str) else ids.get(t)

    nodes = []
    for indice in sorted(entradas):
        nivel, pagina, titulo = entradas[indice]
        seccion = seccion_de(indice)
        if indice in A_NODES:
            pila, verification = 'A', 'instrumented'
            instrumento, umbral = A_NODES[indice]
        elif indice in B_NODES:
            pila, verification, instrumento, umbral = 'B', 'none', None, None
        else:
            pila, verification, instrumento, umbral = 'C', 'none', None, None

        tags = ['htmx', seccion.replace(' ', '-'),
                {'A': 'contractable', 'B': 'no-especificable',
                 'C': 'conocimiento'}[pila]]
        if pila == 'A':
            tags.append('instrumented')

        node = {
            'id': ids[indice],
            'title': titulo,
            'description': '{} (seccion: {}).'.format(titulo, seccion),
            'type': 'Concept',
            'tags': tags,
            'pile': pila,
            'verification': verification,
            'locator': 'pagina {}, H{}'.format(pagina, nivel),
            'alias': ALIAS.get(indice, []),
            'links': [d for d in (destino(t) for t in LINKS.get(indice, [])) if d],
        }
        if instrumento:
            node['instrument'] = instrumento
        if umbral:
            node['threshold'] = umbral
        if indice in WHY_NOT:
            node['why_not'] = WHY_NOT[indice]
        if indice in NOTA_CRUZADA:
            node['body'] = NOTA_CRUZADA[indice]
        nodes.append(node)

    return {
        'source': {
            'slug': 'htmx',
            'title': 'htmx ~ Documentation',
            'author': 'Big Sky Software',
            'file': 'htmx.org/docs (PDF, 52 paginas)',
            'pages': 52,
            'extracted_with': 'pymupdf (tamano de fuente y geometria)',
            'tags': ['fuente', 'documentacion', 'htmx'],
            'corpus': ('Los 59 titulos de seccion del documento (H2 y H3), extraidos '
                       'por tamano de fuente porque el PDF no trae marcadores. '
                       'CORPUS MAS DEBIL QUE EL DE LOS TRES LIBROS: es documentacion '
                       'de referencia, describe una API y no cataloga tecnicas, asi '
                       'que casi la mitad cae en pila C por definicion del genero.'),
        },
        'nodes': nodes,
    }, entradas


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('toc', nargs='?', default=os.path.join('books', 'htmx-toc.txt'))
    parser.add_argument('-o', '--out', default=os.path.join('books', 'htmx.json'))
    args = parser.parse_args(argv)

    with open(args.toc, 'r', encoding='utf-8') as fh:
        spec, entradas = build(fh.read())

    os.makedirs(os.path.dirname(args.out) or '.', exist_ok=True)
    with open(args.out, 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(spec, fh, ensure_ascii=False, indent=2)
        fh.write('\n')

    total = len(spec['nodes'])
    pilas = {'A': 0, 'B': 0, 'C': 0}
    for n in spec['nodes']:
        pilas[n['pile']] += 1
    print('OK: {} nodos -> {}'.format(total, args.out))
    print('  A={} ({:.1f}%)  B={}  C={}'.format(
        pilas['A'], 100.0 * pilas['A'] / total, pilas['B'], pilas['C']))
    print('\n  fraccion medible por seccion:')
    for desde, hasta, nombre in SECCIONES:
        de_la = [i for i in entradas if desde <= i <= hasta]
        if not de_la:
            continue
        a = sum(1 for i in de_la if i in A_NODES)
        if a or len(de_la) >= 3:
            print('    {:<26} {}/{:<3} {:>5.1f}%'.format(
                nombre, a, len(de_la), 100.0 * a / len(de_la)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
