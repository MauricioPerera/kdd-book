#!/usr/bin/env python3
"""Construye books/zen-of-python.json a partir del triaje de PEP 20 (The Zen of Python).

PEP 20 (The Zen of Python, por Tim Peters) es una lista cerrada de 19 aforismos
que `python -c "import this"` imprime verbatim. Este script los toma del archivo
`zen-of-python.txt` (la captura verbatim de ese comando) y los tria a mano en
pilas A/B/C segun el metodo kdd:

  - pila A (contractable/instrumentada): el autor operacionalizo una propiedad
    de texto con un umbral que un artefacto puede leer. Ningun aforismo lo hace
    aqui, asi que A = 0.
  - pila B (tecnica real, sin propiedad definitoria medible): el aforismo
    describe una tecnica real pero no operacionaliza un umbral concreto, o el
    instrumento existente es un superconjunto (falsas positivas). Se registra
    el `why_not` por que no es contractable.
  - pila C (conocimiento): juicio estetico, filosofico o humor sin tecnica
    operacionalizable.

El aforismo de excepciones silenciosas (zp10) es el caso decisivo: el
instrumento relacionado `arch_checks.excepciones` mide para arquitectura-java
"sin catch mudos ni demasiado amplios", un SUPERCONJUNTO del aforismo, porque su
flag "demasiado amplio" dispara sobre `except Exception as e: log(e)` (ancho
captura que maneja el error) que Zen PERMITE por no ser silencioso. Reusarlo
fielmente produce falsas positicas sistemicas, y no se puede inventar un
instrumento nuevo: por eso zp10 es B, no A. Con A = 0 no hay contratos que
emitir (gate 2 no aplica), y la cobertura per-rule de test_cobertura se mantiene
en verde sin ejercicios nuevos ni instrumentos nuevos.

Entrada:
    zen-of-python.txt   captura verbatim de `python -c "import this"` (19 lineas)

Uso:
    python build_zen_of_python.py [zen-of-python.txt] [-o books/zen-of-python.json]
"""

__all__ = ['build', 'leer', 'main']

import argparse
import json
import os
import sys

# Pila A: (instrumento, umbral). 0 de 19 — ningun aforismo operacionaliza una
# propiedad de texto con un umbral automatizado fiel.
A_NODES = {}

# Pila B: tecnica real cuya propiedad definitoria no es medible por artefacto.
# 7 de 19.
B_NODES = {2, 5, 10, 11, 13, 17, 18}

# Pila C: conocimiento, estetica o juicio sin tecnica operacionalizable.
# 12 de 19.
C_INDICES = {1, 3, 4, 6, 7, 8, 9, 12, 14, 15, 16, 19}

# Razon por la que cada B no es contractable (pila B).
WHY_NOT = {
    2: ('Ser explicito es un juicio sobre conducta visible del codigo —nombres, '
        'importaciones, efectos secundarios— y no una sola propiedad de texto. Un '
        'proxy como prohibir `import *` es debil: el aforismo prescribe '
        'explicitidad sobre el conjunto, asi que forzarlo en cada archivo '
        'inventaria una regla que el autor no operacionaliza con un umbral '
        'concreto.'),
    5: ("'Flat es better than nested' reduce a profundidad de anidamiento, pero "
        'el aforismo no fija un umbral numerico: decir cuanto nesting es demasiado '
        'exige un numero ajeno al texto. Sin artefacto que soporte el umbral '
        '(como el de ciclamaticidad de arquitectura), cualquier reuse forzaria un '
        'valor que Zen no decide, convirtiendo el proxy en regla inventada.'),
    10: ('El aforismo prohibe pasar errores silenciosamente, pero el instrumento '
        'relacionado `arch_checks.excepciones` mide para arquitectura-java la '
        'regla "sin catch mudos ni demasiado amplios", un superconjunto: su flag '
        '"demasiado amplio" dispara sobre `except Exception as e: log(e)` —un ancho '
        'captura que maneja el error— que Zen PERMITE por no ser silencioso, dando '
        'una falsa positica sistemica. Un umbral sobre artefacto no juzga la '
        'intencionalidad del cuerpo (log, reraise, return con efecto), asi que la '
        'propiedad definitoria no es automatizable fielmente aqui y la tecnica se '
        'registra en pila B.'),
    11: ("'Unless explicitly silenced' es la excepcion al aforismo anterior: "
        'juzga intencionalidad, no texto. Decidir si un manejador silencia '
        '"explicitamente" necesita razonamiento de flujo sobre el cuerpo (log, '
        'reraise, return con efecto), no un umbral sobre el artefacto; por eso es '
        'human_rubric, no instrumented.'),
    13: ("'One obvious way' apela a lo intuitivo: 'obvious' es un juicio de "
        'legibilidad, no una propiedad de texto. El proxy DRY (duplicacion de '
        'codigo) mide algo relacionado pero no identico: una linea repetida no '
        'implica que haya "muchas formas de hacerlo", asi que el proxy senalaria '
        'correcto aquello que el aforismo no prescribe.'),
    17: ("'Hard to explain is a bad idea' —saber si una implementacion es "
        'explicable depende del lector y del contexto, no de una regla sobre el '
        'texto. Un umbral no decide "es dificil de explicar"; se trata de un juicio '
        'de revision humana, no de una invariante de artefacto.'),
    18: ("'Easy to explain may be a good idea' complementa al anterior: 'facil de "
        'explicar" es juicio de comprensibilidad humana. No hay propiedad textual '
        'que lo determine; se revisa con razon humano, no con un instrumento sobre '
        'el artefacto.'),
}

# Nombres canonigos reconocidos (alias) por aforismo. Las B llevan alias no vacio
# (para busqueda cruzada y enlace entre libros); las C, alias vacio.
ALIAS = {
    1: [],
    2: ['explicito', 'implicito', 'explicit imports', 'no wildcard imports',
        'sin import *'],
    3: [],
    4: [],
    5: ['flat is better than nested', 'plano', 'anidado', 'nesting depth',
        'profundidad'],
    6: [],
    7: [],
    8: [],
    9: [],
    10: ['excepciones', 'except silencioso', 'mudos', 'silent except',
         'errores silenciosos'],
    11: ['silenciamiento explicito', 'explicitly silenced', 'handled exception',
         'excepcion manejada', 'silencio explicito'],
    12: [],
    13: ['one obvious way', 'una sola via', 'obvious way',
         'single canonical way', 'no mas de una forma'],
    14: [],
    15: [],
    16: [],
    17: ['hard to explain', 'mala idea', 'bad idea', 'dificil de explicar',
         'implementation hard to explain'],
    18: ['easy to explain', 'buena idea', 'good idea', 'facil de explicar',
         'implementation easy to explain'],
    19: [],
}

# Titulos cortos (etiquetas) por aforismo — el titulo es una etiqueta que cambia
# con la edicion; el id (zpNN) es estable y no depende del titulo.
TITULOS = {
    1: 'Belleza sobre fealdad',
    2: 'Explicito sobre implicito',
    3: 'Simple sobre complejo',
    4: 'Complejo sobre complicado',
    5: 'Plano sobre anidado',
    6: 'Escaso sobre denso',
    7: 'La legibilidad cuenta',
    8: 'No romper reglas por casos especiales',
    9: 'Practicidad sobre pureza',
    10: 'Errores no silenciosos',
    11: 'Salvo silencio explicito',
    12: 'Ante la ambiguidad, no adivinar',
    13: 'Una sola via obvia',
    14: 'A la holandesa no le es obvio',
    15: 'Ahora sobre nunca',
    16: 'Nunca sobre prematuro',
    17: 'Si cuesta explicar: mala idea',
    18: 'Si se explica facil: buena idea',
    19: 'Namespaces: gran idea',
}

SOURCE = {
    'slug': 'zen-of-python',
    'title': 'The Zen of Python (PEP 20)',
    'author': 'Tim Peters',
    'file': 'peps.python.org/pep-0020',
    'pages': 19,
    'extracted_with': 'triaje a mano de los 19 aforismos de PEP 20 (The Zen of '
                      'Python, por Tim Peters), tomados verbatim de '
                      '`python -c "import this"`. La cobertura instrumentada es '
                      '0% porque ningun aforismo operacionaliza una propiedad de '
                      'texto con un umbral automatizado fiel.',
    'tags': ['fundamento', 'python', 'estilo'],
    'corpus': 'Lista cerrada de 19 aforismos del PEP 20 (The Zen of Python, por '
              'Tim Peters), tomados verbatim de `python -c "import this"`. Es un '
              'corpus finito y deliberado: cada aforismo es un juicio sobre estilo, '
              'legibilidad e intencionalidad. La fraccion instrumentada es 0%: el '
              'aforismo de excepciones silenciosas reusa el espacio de '
              'arquitectura-java, pero su instrumento (`arch_checks.excepciones`) '
              'es un superconjunto que produce falsas positivas sobre '
              '`except Exception as e: log(e)` —que Zen permite—, asi que no hay '
              'regla aislada fiel y no se inventa una nueva.',
}

LOCATOR = 'peps.python.org/pep-0020'

_PILA_TAG = {'A': 'contractable', 'B': 'no-especificable', 'C': 'conocimiento'}


def leer(texto):
    """Indexa la captura verbatim de `import this` por numero de aforismo.

    Saltea la linea de titulo y las lineas en blanco; el resto, en orden, son
    los 19 aforismos (descripcion verbatim del autor).
    """
    out = {}
    idx = 0
    for linea in texto.splitlines():
        s = linea.strip()
        if not s or s.startswith('The Zen of Python'):
            continue
        idx += 1
        out[idx] = s
    return out


def build(texto):
    """Arma el spec de la fuente a partir de la captura verbatim y el triaje."""
    entradas = leer(texto)
    faltan = [i for i in list(A_NODES) + sorted(B_NODES) + sorted(C_INDICES)
              if i not in entradas]
    if faltan:
        raise SystemExit(
            'ERROR: indices del triaje que no existen en la captura: {}'
            .format(faltan))

    if len(entradas) != 19:
        raise SystemExit(
            'ERROR: la captura tiene {} aforismos, se esperaban 19'
            .format(len(entradas)))

    nodes = []
    for indice in sorted(entradas):
        if indice in A_NODES:
            pila, verification = 'A', 'instrumented'
            instrumento, umbral = A_NODES[indice]
        elif indice in B_NODES:
            pila, verification, instrumento, umbral = (
                'B', 'human_rubric', None, None)
        else:
            pila, verification, instrumento, umbral = (
                'C', 'none', None, None)

        tags = ['zen', 'python', 'estilo', _PILA_TAG[pila]]
        if pila == 'A':
            tags.append('instrumented')

        node = {
            'id': 'zp{:02d}'.format(indice),
            'title': TITULOS[indice],
            'description': entradas[indice],
            'type': 'Concept',
            'tags': tags,
            'pile': pila,
            'verification': verification,
            'locator': LOCATOR,
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

    return {'source': SOURCE, 'nodes': nodes}, entradas


def main(argv=None):
    """Lee la captura verbatim, arma el JSON de la fuente y lo escribe."""
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('zen', nargs='?', default='zen-of-python.txt',
                        help='captura verbatim de `python -c "import this"`')
    parser.add_argument('-o', '--out',
                        default=os.path.join('books', 'zen-of-python.json'))
    args = parser.parse_args(argv)

    with open(args.zen, 'r', encoding='utf-8') as fh:
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
    print('  (corpus finito de 19 aforismos de PEP 20; la cobertura '
          'instrumentada es 0%)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
