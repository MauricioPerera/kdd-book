#!/usr/bin/env python3
"""Instrumentos de texto que miden las tres tecnicas contractables de Effective Go.

Renueva el esqueleto de instruments/semver_checks.py con el mismo contrato:
lee artefactos Go (.go) como texto, expone
`check_<regla>(fuentes, opts) -> [(ruta, linea, detalle)]`, un diccionario
`RULES` y una funcion `main()` con los mismos codigos de salida (0 / 1 / 2).

Solo tres reglas son specificables por texto de forma limpia (pila A):

    indentation-tabs    -> gofmt usa tabs; espacios en la sangria son violacion
    no-paren-control    -> if/for/switch no llevan parentesis alrededor de la condicion
    brace-next-line     -> la llave de apertura va en la misma linea que la keyword

El resto de las convenciones de Effective Go (doc comments, comma-ok, defer-close,
error strings, nombrado de paquetes, etc.) se documenta como `verification: none`
en el libro de conocimiento; esas tecnicas requieren analisis semantico o de flujo
que excede un instrumento de texto sobre archivos aislados.

Exit codes (convencion KDD):
  0  la propiedad se cumple
  1  no se cumple
  2  no se pudo verificar (falta el dato, o no hay que medir)

Uso:
    python effective_go_checks.py --rule indentation-tabs <proyecto>
    python effective_go_checks.py --rule no-paren-control <proyecto>
    python effective_go_checks.py --rule brace-next-line <proyecto>
    python effective_go_checks.py --list
"""

__all__ = [
    'ALIASES',
    'ARTEFACTO',
    'NoVerificable',
    'RULES',
    'check_brace_next_line',
    'check_indentation_tabs',
    'check_no_paren_control',
    'main',
]

import argparse
import os
import re
import sys


# Sobre que mide esta familia: el proyecto entero (todo .go).
ARTEFACTO = 'proyecto'

# Alias vacio: los nombres de regla son el nombre canónico del nodo.
ALIASES = {}

_DIRS_EXCLUIDOS = {'__pycache__', '.git', 'tests', 'target', '.cargo', 'node_modules'}

# Una linea con sangria en espacios (uno o mas espacios al inicio) que luego
# tiene contenido no espacios. Tabulaciones al inicio no coinciden.
_RE_SANGRIA_ESPACIOS = re.compile(r'^( +)\S')

# if/for/switch seguido de un parentesis abierto (con cero o mas espacios
# entre la keyword y el '('). No coincide con llamadas a funciones como
# `foo(x)` porque \b exige frontera de palabra antes de if/for/switch.
_RE_PAREN_CONTROL = re.compile(r'\b(if|for|switch)\s*\(')

# Una linea que empieza (tras espacios) con una keyword de estructura de control.
_RE_CONTROL_INICIO = re.compile(r'^\s*(if|for|switch)\b')


class NoVerificable(Exception):
    """El proyecto no expone artefactos que este instrumento pueda leer."""


def _fuentes(proyecto):
    """(ruta, texto) de cada .go del proyecto.

    Se excluyen las pruebas a propósito (``_test.go``) y en todas las reglas:
    un fixture con sangria en espacios es exactamente lo que un fixture debe
    tener, y marcarlo pondria el instrumento en rojo por hacer bien las cosas.
    Los directorios transversales (``__pycache__``, ``.git``, ``tests``,
    ``target``, ``.cargo``) se prunningean in-situ.
    """
    out = []
    for raiz, dirs, archivos in os.walk(proyecto):
        dirs[:] = [d for d in dirs if d not in _DIRS_EXCLUIDOS]
        for nombre in sorted(archivos):
            if not nombre.endswith('.go') or nombre.endswith('_test.go'):
                continue
            ruta = os.path.join(raiz, nombre)
            try:
                with open(ruta, 'r', encoding='utf-8') as fh:
                    texto = fh.read()
            except (OSError, UnicodeDecodeError) as exc:
                raise NoVerificable(
                    'no se pudo leer {}: {}'.format(ruta, exc))
            out.append((ruta, texto))
    if not out:
        raise NoVerificable(
            'el proyecto no tiene fuentes .go que medir')
    return out


def check_indentation_tabs(fuentes, opts):
    """gofmt usa tabulaciones. Un .go con espacios en la sangria es rojo.

    Effective Go: "indent with tabs". Cada linea cuyo primer caracter no blanco
    sea un espacio (en vez de un tab) cuando hay contenido despues es
    violacion. Las lineas dentro de comentarios de bloque ``/* ... */`` se
    excluyen: gofmt preserva su contenido textual.
    """
    out = []
    for ruta, texto in fuentes:
        en_bloque = False
        for i, linea in enumerate(texto.splitlines(), 1):
            if en_bloque:
                if '*/' in linea:
                    en_bloque = False
                continue
            if '/*' in linea:
                resto = linea.split('/*', 1)[1]
                if '*/' not in resto:
                    en_bloque = True
                # La parte anterior al /* podria tener sangria en espacios.
                antes = linea[:linea.index('/*')]
                linea = antes
            m = _RE_SANGRIA_ESPACIOS.match(linea)
            if m:
                out.append((ruta, i,
                            'sangria con {} espacio(s) en vez de tab '
                            '(gofmt usa tabulaciones)'.format(
                                len(m.group(1)))))
    return out


def check_no_paren_control(fuentes, opts):
    """if/for/switch no llevan parentesis alrededor de la condicion.

    Effective Go: "Go's if, for, and switch statements do not use
    parentheses". Una linea con ``if (cond)``, ``for (init; cond; post)``
    o ``switch (expr)`` es violacion. La keyword debe ser seguida
    directamente del cuerpo de la condicion o del ``{`` de apertura.

    Nota: no se buscan parentesis en llamadas a funciones (``foo(x)``)
    porque la frontera de palabra ``\\b`` exige que if/for/switch sea un
    token independiente.
    """
    out = []
    for ruta, texto in fuentes:
        for i, linea in enumerate(texto.splitlines(), 1):
            m = _RE_PAREN_CONTROL.search(linea)
            if m:
                keyword = m.group(1)
                out.append((ruta, i,
                            '{} lleva parentesis alrededor de la condicion '
                            '(Go no usa parentesis en estructuras de '
                            'control)'.format(keyword)))
    return out


def check_brace_next_line(fuentes, opts):
    """La llave de apertura va en la misma linea que if/for/switch/func.

    Effective Go: "The opening brace of a block must be on the same line as
    the if statement". Una linea que empieza con if/for/switch (tras
    espacios) y que NO termina con ``{`` —y cuya linea siguiente empieza
    con ``{``— es violacion: la llave esta en la linea de abajo, estilo C/Java.
    """
    out = []
    for ruta, texto in fuentes:
        lineas = texto.splitlines()
        for i in range(len(lineas) - 1):
            actual = lineas[i].rstrip()
            if not _RE_CONTROL_INICIO.match(actual):
                continue
            if actual.endswith('{'):
                continue
            numero_linea = i + 1
            siguiente = lineas[numero_linea].lstrip()
            if siguiente.startswith('{'):
                keyword = _RE_CONTROL_INICIO.match(actual).group(1)
                out.append((ruta, numero_linea,
                            'la llave de apertura de {} va en linea '
                            'separada: el opening brace debe estar en la misma '
                            'linea que {}'.format(keyword, keyword)))
    return out


RULES = {
    'indentation-tabs': (check_indentation_tabs,
                         'Indentacion con tabulaciones (gofmt): '
                         'cero espacios en la sangria'),
    'no-paren-control': (check_no_paren_control,
                         'Sin parentesis en if/for/switch: '
                         'cero parentesis alrededor de la condicion'),
    'brace-next-line': (check_brace_next_line,
                        'Llave de apertura en la misma linea que '
                        'if/for/switch: cero llaves en linea separada'),
}


def main(argv=None):
    """Corre la regla pedida sobre los archivos dados y devuelve exit code."""
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--rule')
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--proyecto',
                        help='raiz del proyecto (por defecto, la del target)')
    parser.add_argument('target', nargs='?')
    args = parser.parse_args(argv)

    if args.list:
        for nombre in sorted(RULES):
            print('{:24} {}'.format(nombre, RULES[nombre][1]))
        return 0

    if args.rule not in RULES:
        print('NO-VERIFICABLE: regla desconocida: {!r} (ver --list)'.format(
            args.rule))
        return 2
    if not args.target and not args.proyecto:
        print('NO-VERIFICABLE: falta el punto de entrada del proyecto')
        return 2

    if args.proyecto:
        args.proyecto = os.path.abspath(args.proyecto)
    else:
        args.proyecto = os.path.dirname(os.path.abspath(args.target))
    if not os.path.isdir(args.proyecto):
        print('NO-VERIFICABLE: no existe el proyecto {}'.format(
            args.proyecto))
        return 2

    func, etiqueta = RULES[args.rule]
    try:
        fuentes = _fuentes(args.proyecto)
        violaciones = func(fuentes, args)
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
