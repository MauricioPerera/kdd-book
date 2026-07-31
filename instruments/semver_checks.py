#!/usr/bin/env python3
"""Instrumentos que miden las tres tecnicas contractables del SemVer 2.0.0.

Familia nueva sobre un artefacto distinto al de stripe/entorno: no es HTTP ni
el entorno de ejecucion, es el **string de version** que un proyecto publica.
El SemVer 2.0.0 nombra 11 reglas; de esas, tres miden una propiedad del codigo
que se puede exigir como invariante: el formato `X.Y.Z` (articulo 2), los
identificadores de pre-release (articulo 9) y los de build metadata (articulo
10). Las otras ocho (major cero, inmutabilidad, precedence, etc.) son juicios
de proceso, politica o conocimiento, y por eso quedan en pilas B/C sin
instrumento.

Las tres reglas here mirror the exact prose of each article:

    formato     X.Y.Z con enteros no negativos, sin ceros iniciales y sin
                sufijo pre-release ni de build (articulo 2: "a normal version
                number MUST take the form X.Y.Z ... MUST NOT contain leading
                zeroes").
    prerelease  los identificadores de pre-release son no vacios, de solo
                [0-9A-Za-z-], e identificadores numericos sin cero inicial
                (articulo 9).
    build       los identificadores de build metadata son no vacios y de solo
                [0-9A-Za-z-] (articulo 10). A diferencia del pre-release, los
                identificadores numericos de build SI pueden tener ceros
                iniciales.

**Lo que estas reglas no pueden ver, dicho de entrada.** No hay parser de
versiones real: se lee el codigo Python via `ast`, igual que `stripe_checks` y
`entorno_checks`. Solo se inspeccionan literales de string asignados a
`__version__`. Una version armada por concatenacion, format string o calculada
en tiempo de ejecucion no la ve nadie —no es un string literal—, y eso no es
un defecto del instrumento: es el limite de leer el codigo en vez de ejecutuirlo.

Exit codes (convencion KDD):
  0  la propiedad se cumple
  1  no se cumple
  2  no se pudo verificar (falta el dato, o no hay que medir)

Uso:
    python semver_checks.py --rule formato <entrada.py>
    python semver_checks.py --rule prerelease <entrada.py>
    python semver_checks.py --rule build <entrada.py>
    python semver_checks.py --list
"""

__all__ = [
    'NoVerificable',
    'check_formato',
    'check_prerelease',
    'check_build',
    'main',
]

import argparse
import ast
import os
import re
import sys

# Sobre que mide esta familia: el proyecto entero (todo .py que no sea prueba).
ARTEFACTO = 'proyecto'

# Un componente numerico sin cero inicial: "0" o "[1-9][0-9]*".
_NUMERO = r'(?:0|[1-9][0-9]*)'
# Formato X.Y.Z de la version normal (articulo 2). Ningun pre/release ni build.
_VER_CORE = re.compile(r'\A' + _NUMERO + r'\.' + _NUMERO + r'\.' + _NUMERO + r'\Z')
# Un pre-release (o build) identificador: ASCII alfanumerico y guion, no vacio.
_IDENT = re.compile(r'\A[0-9A-Za-z-]+\Z')
# Una version con pre-release: X.Y.Z-<identificadores>.
_VER_CON_PRE = re.compile(r'\A[0-9]+\.[0-9]+\.[0-9]+-(.+)\Z')
# Una version con build metadata: ...<algo>+<identificadores>.
_BUILD_DE = re.compile(r'\+(.+)\Z')


class NoVerificable(Exception):
    """Falta el dato sin el cual la regla no se puede evaluar (exit 2)."""


def _fuentes(proyecto):
    """(ruta, arbol, texto) de cada .py del proyecto que no sea prueba.

    Se excluyen las pruebas a proposito y en todas las reglas: un string de
    version de mentira en un fixture es exactamente lo que un fixture tiene que
    tener, y marcarlo pondria el instrumento en rojo por hacer bien las cosas.
    """
    out = []
    for raiz, dirs, archivos in os.walk(proyecto):
        dirs[:] = [d for d in dirs if d not in ('__pycache__', '.git', 'tests')]
        for nombre in sorted(archivos):
            if not nombre.endswith('.py') or nombre.startswith('test_'):
                continue
            ruta = os.path.join(raiz, nombre)
            try:
                with open(ruta, 'r', encoding='utf-8') as fh:
                    texto = fh.read()
                out.append((ruta, ast.parse(texto), texto))
            except (OSError, SyntaxError, UnicodeDecodeError) as exc:
                raise NoVerificable('no se pudo leer {}: {}'.format(ruta, exc))
    if not out:
        raise NoVerificable('el proyecto no tiene fuentes .py que medir')
    return out


def _literales_asignados(arbol):
    """(linea, nombre, valor) de cada asignacion de un string literal a un nombre.

    Reconoce tanto asignaciones simples (`__version__ = "1.2.3"`) como anotadas
    (`__version__: str = "1.2.3"`), igual que `entorno_checks`.
    """
    out = []
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, (ast.Assign, ast.AnnAssign)):
            continue
        valor = nodo.value
        if not isinstance(valor, ast.Constant) or not isinstance(valor.value, str):
            continue
        objetivos = nodo.targets if isinstance(nodo, ast.Assign) else [nodo.target]
        for objetivo in objetivos:
            if isinstance(objetivo, ast.Name):
                out.append((nodo.lineno, objetivo.id, valor.value))
            elif isinstance(objetivo, ast.Attribute):
                out.append((nodo.lineno, objetivo.attr, valor.value))
    return out


def _versiones(fuentes):
    """[(ruta, linea, valor)] de cada string literal asignado a __version__."""
    out = []
    for archivo, arbol, _texto in fuentes:
        for linea, nombre, valor in _literales_asignados(arbol):
            if nombre == '__version__':
                out.append((archivo, linea, valor))
    return out


def _cero_inicial(ident):
    """Si `ident` es un identificador numerico con cero inicial (no "0")."""
    return ident.isdigit() and not re.fullmatch(_NUMERO, ident)


def check_formato(fuentes, opts):
    """X.Y.Z con enteros no negativos, sin ceros iniciales y sin sufijo.

    Articulo 2 del SemVer 2.0.0: "A normal version number MUST take the form
    X.Y.Z where X, Y, and Z are non-negative integers, and MUST NOT contain
    leading zeroes." Las reglas aqui son: tres componentes numericos separados
    por puntos, cada uno sin cero inicial, y nada de sufijo pre-release ni de
    build (esa es otra regla).
    """
    out = []
    for archivo, linea, valor in _versiones(fuentes):
        if not _VER_CORE.match(valor):
            out.append((archivo, linea,
                        '__version__ = {!r} no cumple el formato X.Y.Z: '
                        'enteros no negativos, sin ceros iniciales y sin '
                        'sufijo pre-release ni build'.format(valor)))
    return out


def check_prerelease(fuentes, opts):
    """Identificadores de pre-release validos.

    Articulo 9: los identificadores deben ser no vacios, de solo
    [0-9A-Za-z-], e identificadores numericos sin cero inicial. Las versiones
    sin pre-release no se verifican aqui (no hay nada que medir) y salen verdes.
    """
    out = []
    for archivo, linea, valor in _versiones(fuentes):
        m = _VER_CON_PRE.match(valor)
        if not m:
            continue
        # Si tambien hay build metadata, descartala: los identificadores que
        # importan son los del pre-release.
        pre = m.group(1).split('+', 1)[0]
        for ident in pre.split('.'):
            if ident == '':
                out.append((archivo, linea,
                            '__version__ = {!r} tiene un identificador de '
                            'pre-release vacio'.format(valor)))
                break
            if not _IDENT.match(ident):
                out.append((archivo, linea,
                            '__version__ = {!r} tiene el identificador de '
                            'pre-release {!r} con caracteres fuera de '
                            '[0-9A-Za-z-]'.format(valor, ident)))
                break
            if _cero_inicial(ident):
                out.append((archivo, linea,
                            '__version__ = {!r} tiene el identificador numerico '
                            'de pre-release {!r} con cero inicial'.format(
                                valor, ident)))
                break
    return out


def check_build(fuentes, opts):
    """Identificadores de build metadata validos.

    Articulo 10: los identificadores deben ser no vacios y de solo
    [0-9A-Za-z-]. A diferencia del pre-release, los identificadores numericos de
    build SI pueden llevar ceros iniciales (el spec lo permite explicitamente).
    Las versiones sin build metadata no se verifican aqui y salen verdes.
    """
    out = []
    for archivo, linea, valor in _versiones(fuentes):
        m = _BUILD_DE.search(valor)
        if not m:
            continue
        for ident in m.group(1).split('.'):
            if ident == '' or not _IDENT.match(ident):
                out.append((archivo, linea,
                            '__version__ = {!r} tiene el identificador de '
                            'build {!r} invalido: debe ser no vacio y de solo '
                            '[0-9A-Za-z-]'.format(valor, ident)))
                break
    return out


RULES = {
    'formato': (check_formato,
                'Formato: X.Y.Z sin ceros iniciales ni sufijo pre-release/build'),
    'prerelease': (check_prerelease,
                   'Pre-release: identificadores no vacios, [0-9A-Za-z-], sin '
                   'ceros iniciales en los numericos'),
    'build': (check_build,
              'Build metadata: identificadores no vacios y de solo [0-9A-Za-z-]'),
}


def main(argv=None):
    """Corre la regla pedida sobre los archivos dados y devuelve el exit code."""
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--rule')
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--proyecto', help='raiz del proyecto (por defecto, la del target)')
    parser.add_argument('target', nargs='?')
    args = parser.parse_args(argv)

    if args.list:
        for nombre in sorted(RULES):
            print('{:24} {}'.format(nombre, RULES[nombre][1]))
        return 0

    if args.rule not in RULES:
        print('NO-VERIFICABLE: regla desconocida: {!r} (ver --list)'.format(args.rule))
        return 2
    if not args.target and not args.proyecto:
        print('NO-VERIFICABLE: falta el punto de entrada del proyecto')
        return 2

    if args.proyecto:
        args.proyecto = os.path.abspath(args.proyecto)
    else:
        args.proyecto = os.path.dirname(os.path.abspath(args.target))
    if not os.path.isdir(args.proyecto):
        print('NO-VERIFICABLE: no existe el proyecto {}'.format(args.proyecto))
        return 2

    func, etiqueta = RULES[args.rule]
    try:
        violaciones = func(_fuentes(args.proyecto), args)
    except NoVerificable as exc:
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
