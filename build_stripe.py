#!/usr/bin/env python3
"""Construye books/stripe.json a partir de un triaje curado de docs.stripe.com/api.

Decima fuente, y el caso mas extremo de corpus curado hasta ahora -mas que
Tailwind-. docs.stripe.com/api tiene del orden de 750 paginas: el arbol
completo de recursos (Charges, Customers, PaymentIntents, Invoices...) donde
cada pagina lista parametros y tipos de campo. Es referencia por definicion
del genero, igual que las ~195 paginas de clases CSS de Tailwind, pero a una
escala mayor.

Igual que con Tailwind, el triaje fue al reves: **primero se identificaron
las 7 paginas conceptuales** de "Using the API" -las que preceden al arbol de
recursos- y recien despues se construyo el volcado, con solo esas 7. Cada
pagina trae exactamente una tecnica o una referencia, asi que el corpus son 7
nodos, uno por pagina.

**El porcentaje de esta fuente NO es comparable al de las nueve anteriores,**
ni siquiera al de Tailwind. Mide la fraccion contractable de una seleccion de
7 paginas sobre un sitio de ~750: sobre el sitio completo el numero seria
muchisimo mas bajo que el de Tailwind, porque el arbol de recursos no tiene
ninguna pagina prescriptiva.

De las 7, solo 2 tienen una prohibicion concreta y binaria en el propio
texto:

    - Authentication dice, sin condicional, que no hay que embeber una clave
      secreta o restringida en el codigo fuente.
    - Idempotent requests dice, sin condicional, que no hay que enviar
      `Idempotency-Key` en peticiones GET o DELETE porque no tiene efecto.

La otra mitad de Idempotent requests -"usar una clave de idempotencia al
crear o actualizar"- es una recomendacion condicionada ("cuando..."), no una
prohibicion plana, y por eso no entra en el umbral: exigirla en cada POST
seria inventar una regla que el propio texto no da sin condicion.

Sus tecnicas medibles necesitan un artefacto que ninguna de las trece
familias existentes lee: codigo fuente que hace peticiones HTTP a la API de
Stripe. Se nombra el instrumento que haria falta, `stripe_checks`, igual que
se hizo con Tailwind antes de `tailwind_checks`.

Entrada: el volcado curado, una linea por entrada:

    <indice>| H<nivel> | <ancla> | <titulo>

Uso:
    python build_stripe.py [books/stripe-toc.txt] [-o books/stripe.json]
"""

__all__ = ['build', 'leer', 'main']

import argparse
import json
import os
import re
import sys

# Pila A: (instrumento, umbral). 2 de 7.
A_NODES = {
    1: ('stripe_checks.py --rule claves-en-codigo',
        'cero claves secretas o restringidas de Stripe escritas como literal'),
    4: ('stripe_checks.py --rule idempotencia-en-lectura',
        'cero headers Idempotency-Key en peticiones GET o DELETE'),
}

# Pila B: tecnica real cuya propiedad definitoria no es medible.
B_NODES = {5}

# Pila C: referencia, o la propia pagina dice que no prescribe.
C_INDICES = {2, 3, 6, 7}

WHY_NOT = {
    5: ('expandir un campo relacionado con `expand` es una capacidad opcional, '
        'no un correcto/incorrecto: no usarlo no es un defecto, solo un round '
        'trip extra. No hay umbral que aplicarle a una opcion'),
}

ALIAS = {
    1: ['restricted keys', 'claves restringidas', 'api keys', 'secretos en el codigo'],
    4: ['idempotency key', 'clave de idempotencia', 'get y delete'],
    5: ['expand', 'expandir respuestas'],
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


def build(texto):
    """Arma el spec de la fuente a partir del volcado curado."""
    entradas = leer(texto)
    faltan = [i for i in list(A_NODES) + sorted(B_NODES) + sorted(C_INDICES)
              if i not in entradas]
    if faltan:
        raise SystemExit('ERROR: indices del triaje que no existen: {}'.format(faltan))

    ids = {i: 'a{}'.format(i) for i in entradas}

    nodes = []
    for indice in sorted(entradas):
        nivel, ancla, titulo = entradas[indice]
        if indice in A_NODES:
            pila, verification = 'A', 'instrumented'
            instrumento, umbral = A_NODES[indice]
        elif indice in B_NODES:
            pila, verification, instrumento, umbral = 'B', 'none', None, None
        else:
            pila, verification, instrumento, umbral = 'C', 'none', None, None

        tags = ['stripe', 'using-the-api',
                {'A': 'contractable', 'B': 'no-especificable',
                 'C': 'conocimiento'}[pila]]
        if pila == 'A':
            tags.append('instrumented')

        node = {
            'id': ids[indice],
            'title': titulo,
            'description': '{} (seccion: Using the API).'.format(titulo),
            'type': 'Concept',
            'tags': tags,
            'pile': pila,
            'verification': verification,
            'locator': 'docs.stripe.com/api/{}'.format(ancla),
            'alias': ALIAS.get(indice, []),
            'links': [],
        }
        if instrumento:
            node['instrument'] = instrumento
        if umbral:
            node['threshold'] = umbral
        if indice in WHY_NOT:
            node['why_not'] = WHY_NOT[indice]
        nodes.append(node)

    return {
        'source': {
            'slug': 'stripe',
            'title': 'Stripe API Reference (Using the API)',
            'author': 'Stripe',
            'file': 'docs.stripe.com/api',
            'pages': 7,
            'extracted_with': 'triaje curado sobre 7 de ~750 paginas, verificado '
                              'pagina por pagina',
            'tags': ['fuente', 'documentacion', 'api', 'stripe'],
            'corpus': ('7 tecnicas de las 7 paginas de "Using the API", elegidas a '
                       'mano de un sitio de ~750 paginas donde el resto es el arbol '
                       'completo de recursos (Charges, Customers, PaymentIntents...) '
                       'sin tecnica que prescribir. NO ES UN VOLCADO LITERAL, y el '
                       'porcentaje no es comparable ni a las ocho fuentes originales '
                       'ni a Tailwind: mide la fraccion contractable de esta '
                       'seleccion de 7 paginas, no la del sitio.'),
        },
        'nodes': nodes,
    }, entradas


def main(argv=None):
    """Lee el volcado curado, arma el JSON de la fuente y lo escribe."""
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('toc', nargs='?', default=os.path.join('books', 'stripe-toc.txt'))
    parser.add_argument('-o', '--out', default=os.path.join('books', 'stripe.json'))
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
    print('  (fraccion de la SELECCION curada de 7, no del sitio de ~750 paginas)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
