#!/usr/bin/env python3
"""Construye books/tailwind.json a partir de un triaje curado de tailwindcss.com/docs.

Novena fuente, y la primera con un metodo de corpus distinto a las ocho
anteriores. El sitio tiene ~210 paginas y **~195 son referencia de clases
CSS** (`z-index`, `flex-basis`, `border-radius`...): listan valores, no
prescriben una tecnica. Un volcado literal de titulos —el metodo de las ocho
fuentes previas— habria dado un grafo dominado por paginas de lookup, pila C
por definicion del genero, igual que la mitad de htmx pero mas extremo.

Asi que esta vez el triaje fue al reves: **primero se identificaron las 13
paginas prescriptivas** ("Getting started" + "Core concepts", de un total de
~210) y recien despues se construyo el volcado, con solo esas 13. El corpus
son 21 nodos, uno por tecnica dentro de esas paginas —no una por titulo de la
pagina—, porque varias paginas traen mas de una tecnica (Compatibility trae
tres, Styling with utility classes trae tres).

**Esto tiene una consecuencia que hay que decir de entrada: el porcentaje de
esta fuente NO es comparable al de las otras ocho.** Mide la fraccion
contractable de una seleccion hecha a mano para parecer prescriptiva, no la
fraccion contractable del sitio. Sobre el sitio completo el numero seria
mucho mas bajo —mas bajo que htmx— porque el 93% de las paginas son
referencia.

Dentro de la seleccion, sin embargo, aparecen dos de los mejores candidatos de
todo el grafo: `conflicting-utility-classes` y `working-mobile-first` tienen
el par correcto/incorrecto escrito **por el propio autor**, con el mismo
patron que WCAG y PEP 8 —una explicacion del error real y la correccion, en el
propio texto de la documentacion—.

Sus tecnicas medibles necesitan un artefacto que ninguna de las doce familias
existentes lee: HTML o JSX con clases de Tailwind. Se nombra el instrumento
que haria falta, `tailwind_checks`, igual que se hizo con htmx antes de
`html_checks` y con los doce factores antes de `entorno_checks`.

Entrada: el volcado curado, una linea por entrada:

    <indice>| H<nivel> | <ancla> | <titulo>

Uso:
    python build_tailwind.py [books/tailwind-toc.txt] [-o books/tailwind.json]
"""

__all__ = ['build', 'leer', 'main', 'seccion_de']

import argparse
import json
import os
import re
import sys

CL = 'codigo-limpio'

SECCIONES = [
    (1, 10, 'getting started'),
    (11, 21, 'core concepts'),
]

# Pila A: (instrumento, umbral). 10 de 21.
#
# Las diez viven en `tailwind_checks`, familia nueva y la unica que lee HTML o
# JSX con clases de Tailwind. Ninguna de las otras once familias tocaba ese
# artefacto.
A_NODES = {
    1: ('tailwind_checks.py --rule instalacion',
        'el plugin y el import estan declarados'),
    4: ('tailwind_checks.py --rule preprocesadores',
        'cero'),
    5: ('tailwind_checks.py --rule referencia',
        'cero bloques de estilo sin @reference'),
    8: ('tailwind_checks.py --rule utilidades-removidas',
        'cero apariciones de la lista de utilidades removidas o renombradas'),
    9: ('tailwind_checks.py --rule modificador-important',
        'cero clases con el modificador antepuesto'),
    11: ('tailwind_checks.py --rule utilidades-en-conflicto',
        'cero conflictos por elemento'),
    15: ('tailwind_checks.py --rule mobile-first',
        'cero utilidades "mobile" declaradas solo bajo un breakpoint'),
    17: ('tailwind_checks.py --rule theme-variables',
        'cero tokens declarados con :root o anidados'),
    18: ('tailwind_checks.py --rule namespace-color',
        'cero colores custom fuera del namespace'),
    20: ('tailwind_checks.py --rule clases-dinamicas',
        'cero clases dinamicas'),
}

# Pila B: tecnica real cuya propiedad definitoria no es medible.
B_NODES = {2, 6, 10, 12, 13, 16}

# Pila C: referencia, o la propia pagina dice que no prescribe.
C_INDICES = {3, 7, 14, 19, 21}

WHY_NOT = {
    2: ('el plugin de Prettier fija un orden, pero esta pagina no reproduce el '
        'algoritmo —solo enlaza a una entrada de blog aparte—. Sin el algoritmo '
        'declarado en esta fuente no hay umbral que aplicar'),
    6: ('es una recomendacion condicional —"no lo recomendamos si se puede '
        'evitar"— y no una prohibicion. No hay un umbral binario que aplicarle '
        'a un condicional'),
    10: ('el orden depende de que variantes se combinen. No hay una regla '
         'general sin enumerar cada par de variantes, y enumerarlos seria '
         'inventar la regla en vez de leerla'),
    12: ('cuando un valor es realmente "puntual" en vez de merecer un token de '
         'diseno es un juicio sobre el sistema de diseno, no una propiedad del '
         'codigo'),
    13: ('es DRY dicho de nuevo: cuanto es "demasiado larga" una lista de '
         'utilidades para extraerla es el mismo juicio que G5 de Codigo Limpio, '
         'y por el mismo motivo no tiene umbral'),
    16: ('que mecanismo de activacion conviene —preferencia del sistema, clase '
         'manual, atributo de datos— es una decision de producto, no un error '
         'que corregir'),
}

ALIAS = {
    1: ['instalacion', 'installation', 'plugin de vite'],
    2: ['orden de clases', 'class sorting', 'prettier plugin'],
    4: ['preprocesadores', 'sass', 'less', 'stylus'],
    5: ['@reference', 'css modules', 'style blocks'],
    6: ['css modules'],
    8: ['utilidades removidas', 'renamed utilities', 'guia de actualizacion'],
    9: ['modificador important', 'important modifier'],
    10: ['orden de variantes', 'variant stacking order'],
    11: ['utilidades en conflicto', 'conflicting utility classes'],
    12: ['valores arbitrarios', 'arbitrary values'],
    13: ['duplicacion', 'managing duplication', 'DRY'],
    15: ['mobile-first', 'working mobile-first', 'breakpoints'],
    16: ['dark mode', 'modo oscuro'],
    17: ['theme variables', 'variables de tema', '@theme'],
    18: ['colores custom', 'custom colors', '--color-*'],
    20: ['deteccion de clases', 'detecting classes', 'nombres dinamicos'],
}

# Enlaces cruzados. Pocos, y hacia donde de verdad hay vecindad.
LINKS = {
    13: ['{}/g5'.format(CL)],
    18: [17],
}

NOTA_CRUZADA = {
    13: ('Es G5 de Codigo Limpio —duplicacion— visto desde utilidades en vez '
         'de funciones. Martin tampoco le da un umbral a "cuanto es demasiada '
         'duplicacion": los dos autores coinciden en que es un juicio, no una '
         'propiedad que se cuenta.'),
    18: ('Colores custom es el mismo requisito que theme variables —declarar '
         'con `@theme`, en el namespace correcto— aplicado especificamente a '
         '`--color-*`. Se separan porque el autor les dedica paginas '
         'distintas, pero comparten instrumento.'),
    5: ('La misma regla aparece en Functions and directives, bajo `@reference`: '
        'la pagina de compatibilidad la da como excepcion para Vue/Svelte y '
        'CSS modules, y la de directivas la da como sintaxis general. Un solo '
        'nodo cubre las dos.'),
}

_LINEA = re.compile(r'^\s*(\d+)\|\s*H(\d)\s*\|\s*(\S+)\s*\|\s*(.+?)\s*$')


def leer(texto):
    """Indexa el volcado curado por numero de entrada."""
    out = {}
    for linea in texto.splitlines():
        if linea.lstrip().startswith('#'):
            continue
        m = _LINEA.match(linea)
        if m:
            out[int(m.group(1))] = (int(m.group(2)), m.group(3), m.group(4))
    return out


def seccion_de(indice):
    """La seccion del sitio a la que pertenece un indice."""
    for desde, hasta, nombre in SECCIONES:
        if desde <= indice <= hasta:
            return nombre
    return 'sin seccion'


def build(texto):
    """Arma el spec de la fuente a partir del volcado curado."""
    entradas = leer(texto)
    faltan = [i for i in list(A_NODES) + sorted(B_NODES) + sorted(C_INDICES)
              if i not in entradas]
    if faltan:
        raise SystemExit('ERROR: indices del triaje que no existen: {}'.format(faltan))

    ids = {i: 't{:02d}'.format(i) for i in entradas}

    def destino(t):
        """Resuelve un enlace: texto si va a otra fuente, indice si es local."""
        return t if isinstance(t, str) else ids.get(t)

    nodes = []
    for indice in sorted(entradas):
        nivel, ancla, titulo = entradas[indice]
        seccion = seccion_de(indice)
        if indice in A_NODES:
            pila, verification = 'A', 'instrumented'
            instrumento, umbral = A_NODES[indice]
        elif indice in B_NODES:
            pila, verification, instrumento, umbral = 'B', 'none', None, None
        else:
            pila, verification, instrumento, umbral = 'C', 'none', None, None

        tags = ['tailwind', seccion.replace(' ', '-'),
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
            'locator': 'tailwindcss.com/docs/{}'.format(ancla),
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
            'slug': 'tailwind',
            'title': 'Tailwind CSS Documentation (Getting started + Core concepts)',
            'author': 'Tailwind Labs',
            'file': 'tailwindcss.com/docs',
            'pages': 13,
            'extracted_with': 'triaje curado sobre 13 de ~210 paginas, verificado '
                              'pagina por pagina',
            'tags': ['fuente', 'documentacion', 'css', 'tailwind'],
            'corpus': ('21 tecnicas de las 13 paginas de "Getting started" y "Core '
                       'concepts", elegidas a mano de un sitio de ~210 paginas donde '
                       '~195 son referencia de clases CSS sin tecnica que prescribir. '
                       'NO ES UN VOLCADO LITERAL como en las otras ocho fuentes: el '
                       'porcentaje mide la fraccion contractable de esta seleccion, '
                       'no la del sitio, y no es comparable sin decir esto.'),
        },
        'nodes': nodes,
    }, entradas


def main(argv=None):
    """Lee el volcado curado, arma el JSON de la fuente y lo escribe."""
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('toc', nargs='?', default=os.path.join('books', 'tailwind-toc.txt'))
    parser.add_argument('-o', '--out', default=os.path.join('books', 'tailwind.json'))
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
    print('  (fraccion de la SELECCION curada, no del sitio de ~210 paginas)')
    for desde, hasta, nombre in SECCIONES:
        de_la = [i for i in entradas if desde <= i <= hasta]
        a = sum(1 for i in de_la if i in A_NODES)
        print('    {:<18} {}/{:<3} {:>5.1f}%'.format(
            nombre, a, len(de_la), 100.0 * a / len(de_la)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
