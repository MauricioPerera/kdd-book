#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Construye books/rust-api.json a partir de books/rust-api-checklist.txt.

Rodea el mismo contrato que build_semver.py: lee el inventario con la
expresion regular _LINEA, triparticiona los 54 items en pilas A/B/C y
serializa un objeto {source, nodes} que okf_emit.py puede consumir.

Salidas de exit code:
    0 -> JSON escrito y el total de nodos es exactamente 54.
    1 -> el total no es 54 (por ejemplo si se incluyera la ancla
          C-HTML-ROOT que no tiene checkbox).
    2 -> error de E/S o de argumentos.
"""

import argparse
import json
import os
import re
import sys

# ---------------------------------------------------------------------------
# Origen del conocimiento
# ---------------------------------------------------------------------------

SOURCE = {
    'slug': 'rust-api',
    'title': 'Rust API Guidelines Checklist',
    'author': 'rust-lang/api-guidelines (Rust API Guidelines)',
    'file': 'rust-lang.github.io/api-guidelines',
    'pages': 1,
    'extracted_with': 'web_fetch (checklist.md, rust-lang.github.io/api-guidelines)',
    'tags': ['rust', 'api', 'coding-standards', 'guidelines'],
    'corpus': 'rust-api',
}

LOCATOR = 'rust-lang.github.io/api-guidelines'

# Expresion regular que parsea cada linea del inventario:
#   <idx>| H<n> | <codigo> | <texto>
_LINEA = re.compile(r'^\s*(\d+)\|\s*H(\d)\s*\|\s*(\S+)\s*\|\s*(.+?)\s*$')

# ---------------------------------------------------------------------------
# Triage A/B/C
# ---------------------------------------------------------------------------
#
# Pila A: reglas cuantificables por instrumento de texto (regex) con un
# `dont` verde limpio. Tres items: C-GETTER, C-COMMON-TRAITS,
# C-QUESTION-MARK.
# Pila B: items presenciales cuyo instrumento de texto seria un proxy
# frágil (implica parsear TOML SPDX/URI o validar existencia en
# Cargo.toml). Se documenta `why_not`.
# Pila C: resto (conocimiento, no specificable directamente).

A_NODES = {
    3: 'getter',          # C-GETTER
    8: 'common-traits',   # C-COMMON-TRAITS
    23: 'question-mark',  # C-QUESTION-MARK
}

B_NODES = {
    1:  'C-CASE',
    13: 'C-GOOD-ERR',
    26: 'C-METADATA',
    27: 'C-RELNOTES',
    53: 'C-STABLE',
    54: 'C-PERMISSIVE',
}

# Las 54 posiciones; C-HTML-ROOT (ancla de seccion) no tiene checkbox y
# no aparece en el inventario -> exactamente 54 items.
C_INDICES = set(range(1, 55)) - set(A_NODES) - set(B_NODES)

WHY_NOT = {
    1:  'C-CASE: nombrar con convencion de mayusculas/minusculas exige '
        'analisislexico de identificadores Rust (CamelCase, snake_case, '
        'SCREAMING_SNAKE_CASE) y heurísticas de contexto; el instrumento '
        'actual no puede decidir con seguridad sin un parseo lexico y '
        'una base de datos de convenciones, por lo que cualquier proxy '
        'seria demasiado frágil.',
    13: 'C-GOOD-ERR: juzgar que un tipo de error es "significante y '
        'bien comportado" implica inspeccionar mensajes, variantes, '
        'impls de Error/std::error::Error y Send+Sync; una heurística de '
        'texto no puede verificar la semantica de los errores con la '
        'rigidez que merece.',
    26: 'C-METADATA: requiere parsear Cargo.toml como TOML y validar '
        'presencia/ausencia de autores, description, license (con '
        'expresión SPDX), homepage/documentation/repository (URIs), '
        'keywords y categories. Un proxy de presencia de claves es '
        'demasiado frágil y no valida SPDX ni URIs.',
    27: 'C-RELNOTES: la existencia de notas de version depende de archivos '
        'CHANGELOG.md/RELEASES.md y de su contenido (enlazar cada cambio '
        ' significativo). No hay un artefacto de texto unico sobre el '
        'cual aplicar un regex fiable.',
    53: 'C-STABLE: determinar la estabilidad de las dependencias publicas '
        'de un crate estable implica inspeccionar la version y el estado '
        'de estabilidad de cada dependencia transitiva; una heuristica '
        'de texto sobre `Cargo.toml` no puede inferirlo.',
    54: 'C-PERMISSIVE: validar que el crate y sus dependencias tengan una '
        'licencia permansiva implica resolver SPDX de cada dependencia '
        'transitiva y comparar contra la familia de licencias '
        'permisivas; un proxy de texto sobre `license` es frágil.',
}

# Alias canónicos (kebab-case, usados por --rule del instrumento).
ALIAS = {
    3:  'getter',
    8:  'common-traits',
    23: 'question-mark',
}

# Umbral opcional para las reglas instrumentadas (informativo).
THRESHOLD = {
    3:  {'max_violations': 0},
    8:  {'max_violations': 0},
    23: {'max_violations': 0},
}

# Titulos display (kebab-case como en la guía original).
TITULOS = {
    1: 'C-CASE', 2: 'C-CONV', 3: 'C-GETTER', 4: 'C-ITER',
    5: 'C-ITER-TY', 6: 'C-FEATURE', 7: 'C-WORD-ORDER',
    8: 'C-COMMON-TRAITS', 9: 'C-CONV-TRAITS', 10: 'C-COLLECT',
    11: 'C-SERDE', 12: 'C-SEND-SYNC', 13: 'C-GOOD-ERR',
    14: 'C-NUM-FMT', 15: 'C-RW-VALUE', 16: 'C-EVOCATIVE',
    17: 'C-MACRO-ATTR', 18: 'C-ANYWHERE', 19: 'C-MACRO-VIS',
    20: 'C-MACRO-TY', 21: 'C-CRATE-DOC', 22: 'C-EXAMPLE',
    23: 'C-QUESTION-MARK', 24: 'C-FAILURE', 25: 'C-LINK',
    26: 'C-METADATA', 27: 'C-RELNOTES', 28: 'C-HIDDEN',
    29: 'C-SMART-PTR', 30: 'C-CONV-SPECIFIC', 31: 'C-METHOD',
    32: 'C-NO-OUT', 33: 'C-OVERLOAD', 34: 'C-DEREF',
    35: 'C-CTOR', 36: 'C-INTERMEDIATE', 37: 'C-CALLER-CONTROL',
    38: 'C-GENERIC', 39: 'C-OBJECT', 40: 'C-NEWTYPE',
    41: 'C-CUSTOM-TYPE', 42: 'C-BITFLAG', 43: 'C-BUILDER',
    44: 'C-VALIDATE', 45: 'C-DTOR-FAIL', 46: 'C-DTOR-BLOCK',
    47: 'C-DEBUG', 48: 'C-DEBUG-NONEMPTY', 49: 'C-SEALED',
    50: 'C-STRUCT-PRIVATE', 51: 'C-NEWTYPE-HIDE',
    52: 'C-STRUCT-BOUNDS', 53: 'C-STABLE', 54: 'C-PERMISSIVE',
}


def _etiquetas(idx):
    if idx in A_NODES:
        return ['rust-api', 'api', 'contractable', 'instrumented']
    if idx in B_NODES:
        return ['rust-api', 'api', 'no-especificable']
    return ['rust-api', 'api', 'conocimiento']


# ---------------------------------------------------------------------------
# Parseo del inventario
# ---------------------------------------------------------------------------

def leer(ruta):
    """Lee el archivo de inventario y devuelve una lista de diccionarios."""
    items = []
    with open(ruta, encoding='utf-8') as fh:
        for linea in fh:
            m = _LINEA.match(linea)
            if not m:
                continue
            idx = int(m.group(1))
            nivel = m.group(2)
            codigo = m.group(3)
            texto = m.group(4)
            items.append({
                'idx': idx,
                'nivel': nivel,
                'codigo': codigo,
                'texto': texto,
            })
    return items


def build(items):
    nodes = []
    for it in items:
        idx = it['idx']
        nodo = {
            'id': 'c{:02d}'.format(idx),
            'title': TITULOS.get(idx, it['codigo']),
            'description': it['texto'],
            'type': 'Concept',
            'tags': _etiquetas(idx),
            'pile': 'A' if idx in A_NODES else ('B' if idx in B_NODES else 'C'),
            'verification': 'instrumented' if idx in A_NODES else 'none',
            'locator': LOCATOR,
            'alias': [ALIAS[idx]] if idx in ALIAS else [],
            'links': [],
        }
        if idx in A_NODES:
            regla = A_NODES[idx]
            nodo['instrument'] = 'rust_api_checks.py --rule {}'.format(regla)
            nodo['threshold'] = THRESHOLD.get(idx, {})
        if idx in B_NODES:
            nodo['why_not'] = WHY_NOT[idx]
        nodes.append(nodo)
    return {'source': SOURCE, 'nodes': nodes}


def main(argv=None):
    ap = argparse.ArgumentParser(description='Construye books/rust-api.json')
    ap.add_argument('--toc', default='books/rust-api-checklist.txt')
    ap.add_argument('--out', default='books/rust-api.json')
    args = ap.parse_args(argv)

    toc = os.path.abspath(args.toc)
    out = os.path.abspath(args.out)
    try:
        items = leer(toc)
        spec = build(items)
    except OSError as exc:
        sys.stderr.write('build_rust_api: {}\n'.format(exc))
        return 2

    total = len(spec['nodes'])
    n_a = len(spec['nodes']) and sum(
        1 for n in spec['nodes'] if n['pile'] == 'A')
    n_b = sum(1 for n in spec['nodes'] if n['pile'] == 'B')
    n_c = sum(1 for n in spec['nodes'] if n['pile'] == 'C')

    if total != 54:
        sys.stderr.write(
            'build_rust_api: el inventario produjo {} nodos, se esperaban '
            '54\n'.format(total))
        return 1
    if n_a != 3:
        sys.stderr.write(
            'build_rust_api: pila A tiene {} nodos, se esperaban 3\n'
            .format(n_a))
        return 1

    with open(out, 'w', encoding='utf-8') as fh:
        json.dump(spec, fh, ensure_ascii=False, indent=2)
        fh.write('\n')

    sys.stdout.write(
        'build_rust_api: {} nodos (A={}, B={}, C={}) -> {}\n'.format(
            total, n_a, n_b, n_c, out))
    return 0


if __name__ == '__main__':
    sys.exit(main())
