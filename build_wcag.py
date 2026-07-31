#!/usr/bin/env python3
"""Construye books/wcag.json a partir de los titulos de WCAG 2.2.

Sexta fuente, y se eligio para poder **refutar** el hallazgo 2, no para
confirmarlo. Lo que el grafo venia sosteniendo es que la contractabilidad la
decide que el autor haya operacionalizado la tecnica. WCAG es el caso limite:
sus criterios se llaman literalmente *"testable success criteria"* y estan
operacionalizados al maximo por diseno, con umbrales numericos explicitos
—4.5:1 de contraste, 24 por 24 pixeles de area de toque—. Y su artefacto es
HTML, que este repositorio ya sabe leer, asi que tampoco hay donde esconderse.

Prediccion escrita antes de triajar: **va a dar bajo**, por debajo de los libros
de codigo. Si daba mas de 60%, el refinamiento estaba mal.

Dio **11,5%** sobre el documento entero y **13,8%** sobre los criterios solos.

El hallazgo que deja, y es una correccion de lo que decia el grafo: que el autor
haya operacionalizado la tecnica es **necesario y no suficiente**. WCAG dice
"testable" y quiere decir *que una persona formada puede decidir si se cumple*.
Eso no es lo mismo que medible por un instrumento, y la diferencia no es de
grado: 1.1.1 pide una alternativa textual que cumpla **el proposito
equivalente**, y ninguna medicion decide equivalencia de proposito. La condicion
que faltaba es que **lo que el umbral compara este en el artefacto**.

Se ve limpio en los 12 medibles: todos son criterios donde el autor nombro un
MECANISMO decidible —un token de `autocomplete`, un `lang` valido, un `role` con
nombre accesible, una razon de contraste— y no una cualidad del contenido.

**Aviso sobre cuatro de los doce.** Contraste (1.4.3 y 1.4.6) y area de toque
(2.5.5 y 2.5.8) tienen el umbral mas nitido de los 87 y necesitan valores
renderizados, que no estan en el HTML. Se marcan medibles igual, por el mismo
criterio con que `http_checks` mide sobre capturas: el proyecto **declara** el
artefacto. Si no lo declara, exit 2.

Entrada: el volcado de titulos, una linea por entrada:

    <indice>| H<nivel> | <referencia> | <titulo>

Uso:
    python build_wcag.py [books/wcag-toc.txt] [-o books/wcag.json]
"""

import argparse
import json
import os
import re
import sys

HT = 'htmx'

# (primer_indice, ultimo_indice, nombre)
SECCIONES = [
    (1, 34, 'perceptible'),
    (35, 74, 'operable'),
    (75, 99, 'comprensible'),
    (100, 104, 'robusto'),
]

# Pila A: (instrumento, umbral). Doce de 87 criterios.
#
# Diez reglas para doce criterios: `contraste` y `toque` sirven a dos cada una,
# que es lo que pasa cuando el autor da el mismo umbral en dos niveles de
# conformidad distintos (AA y AAA). El instrumento recibe el umbral por
# argumento y el nodo lo declara: es el nodo el que dice que exige.
#
# Contraste y area de toque necesitan valores renderizados que el HTML no tiene.
# El instrumento lee los estilos en linea, que si estan en el artefacto, y lo
# que el proyecto declare con `--medidas` — misma forma que las capturas de
# `http_checks`. Sin nada de eso, exit 2.
A_NODES = {
    19: ('a11y_checks.py --rule autocomplete',
         'cero campos de datos personales sin token de autocomplete'),
    23: ('a11y_checks.py --rule autoplay',
         'cero'),
    24: ('a11y_checks.py --rule contraste --min 4.5 --min-grande 3.0',
         '4.5:1 para texto normal, 3:1 para texto grande'),
    27: ('a11y_checks.py --rule contraste --min 7.0 --min-grande 4.5',
         '7:1 para texto normal, 4.5:1 para texto grande'),
    51: ('a11y_checks.py --rule movimiento',
         'cero animaciones de interaccion sin alternativa reducida'),
    53: ('a11y_checks.py --rule saltar',
         'al menos un mecanismo de salto por pagina'),
    69: ('a11y_checks.py --rule etiquetaennombre',
         'cero controles cuyo nombre accesible no contenga su etiqueta visible'),
    71: ('a11y_checks.py --rule toque --min 44',
         '44 por 44 pixeles CSS'),
    74: ('a11y_checks.py --rule toque --min 24',
         '24 por 24 pixeles CSS'),
    77: ('a11y_checks.py --rule idioma',
         'un lang valido por pagina'),
    92: ('a11y_checks.py --rule etiqueta',
         'cero controles sin etiqueta'),
    103: ('a11y_checks.py --rule nombrerol',
          'cero componentes sin nombre y cero aria invalido para el rol'),
}

# Pila C: lo que no es una tecnica. Los cuatro principios y las trece pautas son
# titulos de organizacion; 4.1.1 lo marca obsoleto el propio documento.
C_INDICES = {1, 2, 4, 14, 21, 35, 36, 41, 48, 52, 66, 75, 76, 83, 90, 100, 101, 102}

WHY_NOT = {
    3: ('pide una alternativa textual que cumpla "el proposito equivalente". '
        'Que el `alt` este es decidible; que sea equivalente no lo decide '
        'ninguna medicion, y equivalente es la palabra del criterio'),
    37: ('"toda la funcionalidad operable por teclado" no es decidible leyendo '
         'la pagina. Lo que si se mide —manejadores de click en elementos no '
         'enfocables— es una parte, y confundir la parte con el criterio seria '
         'dar verde sobre paginas que lo incumplen'),
    54: ('el titulo tiene que "describir el tema o proposito". La presencia se '
         'mide; la descripcion es juicio, igual que en 1.1.1'),
    56: ('el proposito del enlace se juzga contra su contexto: es comprension '
         'de texto, no una propiedad del marcado'),
    58: ('"describen el tema o proposito" otra vez: la existencia de encabezados '
         'se mide, su calidad no'),
    59: ('el indicador de foco tiene que ser visible, y visible se decide al '
         'renderizar. La ausencia de `outline` es una pista, no el criterio'),
    104: ('exige saber cuales mensajes son de estado, y eso es una decision '
          'sobre el significado del contenido'),
}

ALIAS = {
    3: ['texto alternativo', 'alt text', 'non-text content'],
    15: ['info y relaciones', 'info and relationships', 'semantica del marcado'],
    19: ['proposito del campo', 'identify input purpose', 'autocomplete'],
    22: ['uso del color', 'use of color'],
    23: ['control de audio', 'audio control', 'autoplay'],
    24: ['contraste minimo', 'contrast minimum', 'razon de contraste'],
    27: ['contraste mejorado', 'contrast enhanced'],
    37: ['operable por teclado', 'keyboard accessible'],
    38: ['trampa de teclado', 'no keyboard trap'],
    51: ['animacion por interaccion', 'animation from interactions',
         'prefers-reduced-motion'],
    53: ['saltar bloques', 'bypass blocks', 'skip link'],
    54: ['pagina titulada', 'page titled'],
    55: ['orden de foco', 'focus order'],
    59: ['foco visible', 'focus visible'],
    69: ['etiqueta en el nombre', 'label in name'],
    71: ['area de toque mejorada', 'target size enhanced'],
    74: ['area de toque minima', 'target size minimum'],
    77: ['idioma de la pagina', 'language of page', 'lang'],
    78: ['idioma de las partes', 'language of parts'],
    91: ['identificacion de errores', 'error identification'],
    92: ['etiquetas o instrucciones', 'labels or instructions', 'label'],
    103: ['nombre, rol, valor', 'name role value', 'accessible name'],
    104: ['mensajes de estado', 'status messages', 'aria-live'],
}

# Enlaces cruzados. Los dos que cruzan de fuente son los que dicen algo: la
# misma pagina rota, vista por dos autores distintos.
LINKS = {
    24: [27],
    74: [71],
    37: ['{}/20'.format(HT)],
    104: ['{}/10'.format(HT)],
}

NOTA_CRUZADA = {
    37: ('Es el mismo defecto que mide htmx/20 (mejora progresiva) y es el par '
         'mas nitido del grafo, porque los dos autores describen **la misma '
         'pagina rota**: un `<div hx-get>` no es un enlace ni un boton, asi que '
         'ni degrada sin javascript ni se puede operar con el teclado. La '
         'diferencia esta en que fijo cada uno. La documentacion de htmx pide un '
         '`<a href>` o un `<form action>`, que es un mecanismo y se mide. WCAG '
         'pide que "toda la funcionalidad sea operable por teclado", que es el '
         'resultado y no se mide. Por eso htmx/20 esta en pila A y este en B, y '
         'no es que un criterio sea mejor que el otro: el que nombra el '
         'mecanismo se puede instrumentar.'),
    104: ('Toca directamente al indicador de htmx/10: un indicador de carga es '
          'un mensaje de estado, y para que un lector de pantalla lo anuncie '
          'tiene que vivir en una region con `aria-live`. htmx/10 mide que el '
          'indicador **exista**, que es lo que se puede medir; este criterio '
          'pide ademas que **se anuncie**, y eso depende de reconocer cual '
          'contenido es un mensaje de estado.'),
    24: ('Junto con 1.4.6, 2.5.5 y 2.5.8 son los cuatro umbrales mas nitidos de '
         'los 87 —una razon de contraste, un area en pixeles— y los cuatro '
         'necesitan valores **renderizados** que el HTML no tiene. Es el mismo '
         'problema que resolvio `http_checks` sin salir a la red: el proyecto '
         'declara el artefacto medible. Que el umbral sea impecable no alcanza '
         'si lo que compara no esta al alcance.'),
}

_LINEA = re.compile(r'^\s*(\d+)\|\s*H(\d)\s*\|\s*(\S+)\s*\|\s*(.+?)\s*$')
_NIVEL = re.compile(r'\(Level (A{1,3})\)$')


def leer(texto):
    out = {}
    for linea in texto.splitlines():
        if linea.lstrip().startswith('#'):
            continue
        m = _LINEA.match(linea)
        if m:
            out[int(m.group(1))] = (int(m.group(2)), m.group(3), m.group(4))
    return out


def seccion_de(indice):
    for desde, hasta, nombre in SECCIONES:
        if desde <= indice <= hasta:
            return nombre
    return 'sin seccion'


def id_de(referencia):
    """`1.4.13` -> `sc1-4-13`, `1.4` -> `g1-4`, `P1` -> `p1`.

    La numeracion es el identificador del autor y no cambia con la traduccion;
    el titulo si. El separador es un guion y no un punto ni un guion bajo porque
    `okf_emit` exige kebab-case: el id termina siendo un nombre de archivo.
    """
    if referencia.startswith('P'):
        return 'p' + referencia[1:]
    partes = referencia.split('.')
    prefijo = 'sc' if len(partes) == 3 else 'g'
    return prefijo + '-'.join(partes)


def build(texto):
    entradas = leer(texto)
    faltan = [i for i in list(A_NODES) + sorted(C_INDICES) if i not in entradas]
    if faltan:
        raise SystemExit('ERROR: indices del triaje que no existen: {}'.format(faltan))

    ids = {i: id_de(entradas[i][1]) for i in entradas}

    def destino(t):
        return t if isinstance(t, str) else ids.get(t)

    nodes = []
    for indice in sorted(entradas):
        nivel, referencia, titulo = entradas[indice]
        seccion = seccion_de(indice)
        if indice in A_NODES:
            pila, verification = 'A', 'instrumented'
            instrumento, umbral = A_NODES[indice]
        elif indice in C_INDICES:
            pila, verification, instrumento, umbral = 'C', 'none', None, None
        else:
            pila, verification, instrumento, umbral = 'B', 'none', None, None

        tags = ['wcag', seccion,
                {'A': 'contractable', 'B': 'no-especificable',
                 'C': 'conocimiento'}[pila]]
        if pila == 'A':
            tags.append('instrumented')
        conformidad = _NIVEL.search(titulo)
        if conformidad:
            tags.append('nivel-' + conformidad.group(1).lower())

        node = {
            'id': ids[indice],
            'title': titulo,
            'description': '{} (principio: {}).'.format(titulo, seccion),
            'type': 'Concept',
            'tags': tags,
            'pile': pila,
            'verification': verification,
            'locator': 'WCAG 2.2, {}'.format(referencia),
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
            'slug': 'wcag',
            'title': 'Web Content Accessibility Guidelines (WCAG) 2.2',
            'author': 'W3C Accessibility Guidelines Working Group',
            'file': 'w3.org/TR/WCAG22 (recomendacion W3C)',
            'pages': 0,
            'extracted_with': 'titulos del documento, verificados contra la fuente',
            'tags': ['fuente', 'norma', 'accesibilidad'],
            'corpus': ('Los 4 principios, las 13 pautas y los 87 criterios de exito, '
                       'con su nivel de conformidad tal como el documento los escribe. '
                       'Se conserva 4.1.1, que la propia fuente marca "(Obsolete and '
                       'removed)": sacarlo seria editar el corpus. GENERO NUEVO: es '
                       'una norma, y sus criterios estan escritos para ser '
                       'verificables. Que verificable no sea medible es lo que esta '
                       'fuente vino a poner a prueba.'),
        },
        'nodes': nodes,
    }, entradas


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('toc', nargs='?', default=os.path.join('books', 'wcag-toc.txt'))
    parser.add_argument('-o', '--out', default=os.path.join('books', 'wcag.json'))
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
    criterios = [n for n in spec['nodes'] if n['id'].startswith('sc')]
    a_crit = sum(1 for n in criterios if n['pile'] == 'A')
    print('  solo los criterios de exito: {}/{} ({:.1f}%)'.format(
        a_crit, len(criterios), 100.0 * a_crit / len(criterios)))
    for desde, hasta, nombre in SECCIONES:
        de_la = [i for i in entradas if desde <= i <= hasta]
        a = sum(1 for i in de_la if i in A_NODES)
        print('    {:<14} {}/{:<3} {:>5.1f}%'.format(
            nombre, a, len(de_la), 100.0 * a / len(de_la)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
