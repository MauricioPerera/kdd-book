#!/usr/bin/env python3
"""Instrumento de texto para el libro Rust API Guidelines Checklist.

Renueva el esqueleto de instruments/semver_checks.py con identico
contrato: lee artefactos Rust (.rs / Cargo.toml) como texto, expone
`check_<regla>(fuentes, opts) -> [(ruta, linea, detalle)]`, un diccionario
`RULES` y una funcion `main()` con los mismos codigos de salida (0 / 1 / 2).

Solo tres reglas son specificables por texto de forma limpia (pila A):

    getter            -> C-GETTER
    common-traits     -> C-COMMON-TRAITS
    question-mark     -> C-QUESTION-MARK

El resto del checklist (51 items) se documenta como `verification: none`.
"""

__all__ = [
    'ALIASES',
    'NoVerificable',
    'RULES',
    'check_common_traits',
    'check_getter',
    'check_question_mark',
    'main',
]

import argparse
import os
import re
import sys


ARTEFACTO = 'crate'


class NoVerificable(Exception):
    """El proyecto no expone artefactos que este instrumento pueda leer."""


# ---------------------------------------------------------------------------
# Fuentes
# ---------------------------------------------------------------------------

_DIRS_EXCLUIDOS = {'__pycache__', '.git', 'tests', 'target', '.cargo'}


def _fuentes(proyecto):
    """Devuelve el conjunto de fuentes de texto del proyecto.

    {'rust': [(ruta, texto), ...], 'cargo': texto|None, 'cargo_path': path|None}
    """
    proyecto = os.path.abspath(proyecto)
    fuentes = {'rust': [], 'cargo': None, 'cargo_path': None}

    for raiz, dirs, archivos in os.walk(proyecto):
        # Poda de directorios excluidos in-situ.
        dirs[:] = [d for d in dirs if d not in _DIRS_EXCLUIDOS]
        for nombre in sorted(archivos):
            # Ignora archivos de test y artefactos de build.
            if nombre.startswith('test_') or nombre.startswith('$'):
                continue
            ruta = os.path.join(raiz, nombre)
            ext = os.path.splitext(nombre)[1]
            if ext == '.rs':
                try:
                    with open(ruta, encoding='utf-8') as fh:
                        texto = fh.read()
                except OSError:
                    continue
                fuentes['rust'].append((ruta, texto))
            elif nombre == 'Cargo.toml':
                try:
                    with open(ruta, encoding='utf-8') as fh:
                        texto = fh.read()
                except OSError:
                    texto = None
                fuentes['cargo'] = texto
                fuentes['cargo_path'] = ruta

    if not fuentes['rust']:
        raise NoVerificable(
            'No se encontraron archivos .rs bajo {}'.format(proyecto))
    return fuentes


# ---------------------------------------------------------------------------
# Helpers de posicion
# ---------------------------------------------------------------------------

def _linea_de(texto, offset):
    """Numero de linea (1-based) del offset caracter en `texto`."""
    return texto.count('\n', 0, offset) + 1


# ===========================================================================
# Pila A: getters (C-GETTER)
# ===========================================================================

# Un getter con prefijo `get_`: fn get_<nombre>(...) -> <T>
_RE_GETTER = re.compile(
    r'fn\s+(?P<nombre>get_[A-Za-z_]\w*)\s*\((?P<params>[^)]*)\)\s*->\s*'
    r'(?P<retorno>[^;{}\n]+)')


def check_getter(fuentes, opts):
    """C-GETTER: los getters por valor no usan el prefijo `get_`.

    La convencion Rust es que `get_` es exclusivo de getters por
    referencia; un getter que devuelve por valor debe renombrarse
    eliminando el prefijo.
    """
    out = []
    for ruta, texto in fuentes['rust']:
        for m in _RE_GETTER.finditer(texto):
            nombre = m.group('nombre')
            params = m.group('params')
            retorno = m.group('retorno').lstrip()
            if 'self' in params and not retorno.startswith('&'):
                out.append((ruta, _linea_de(texto, m.start()),
                            'getter `{}` devuelve por valor ({}); renombre '
                            'sin prefijo `get_`'.format(nombre, retorno)))
    return out


# ===========================================================================
# Pila A: common traits (C-COMMON-TRAITS)
# ===========================================================================

_RE_PUB_TIPO = re.compile(r'^(?P<indent>\s*)pub\s+(?P<kw>struct|enum)\s+(?P<tipo>\w+)')
_RE_ATTR = re.compile(r'^\s*#\s*\[\s*derive\s*\((?P<args>[^)]*)\)')


def _attr_lines(texto, idx_linea):
    """Generador de lineas de atributos `#[...]` contiguas encima de la
    linea `idx_linea` (0-based)."""
    lineas = texto.splitlines()
    j = idx_linea - 1
    while j >= 0:
        s = lineas[j].strip()
        if _RE_ATTR.match(lineas[j]):
            yield lineas[j], _RE_ATTR.match(lineas[j]).group('args')
            j -= 1
        elif s.startswith('#[') or s.startswith('# ['):
            # Otro atributo (no derive): sigue subiendo.
            j -= 1
        else:
            break


def check_common_traits(fuentes, opts):
    """C-COMMON-TRAITS: tipos publicos implementan Debug.

    Instrumento textual: un `pub struct`/`pub enum` que carece de un
    `#derive(...Debug...)` en los atributos contiguos inmediatos es
    una violacion.
    """
    out = []
    for ruta, texto in fuentes['rust']:
        lineas = texto.splitlines()
        for i, linea in enumerate(lineas):
            m = _RE_PUB_TIPO.match(linea)
            if not m:
                continue
            tipo = m.group('tipo')
            tiene_debug = any('Debug' in (args or '')
                              for _, args in _attr_lines(texto, i))
            if not tiene_debug:
                out.append((ruta, i + 1,
                            'tipo publico `{}` carece de '
                            '#[derive(...Debug...)]'.format(tipo)))
    return out


# ===========================================================================
# Pila A: question mark (C-QUESTION-MARK)
# ===========================================================================

# Linea de doc rustdoc: `/// ...` (tambien cubrimos `//! ...` de modulo).
_RE_DOC = re.compile(r'^//[/!]\s?(.*)$')
_RE_FENCE = re.compile(r'```')           # abre / cierra bloque de codigo
_RE_BAD = re.compile(r'\.unwrap\(\)|try!\s*\(')


def _doc_violations(ruta, texto):
    """Lineas de `.unwrap()` / `try!(...)` dentro de un bloque de codigo
    rustdoc (`///` con ``` ``` ```)."""
    out = []
    en_fenced = False     # dentro de un bloque de codigo
    for i, linea in enumerate(texto.splitlines(), 1):
        m = _RE_DOC.match(linea.lstrip())
        if m:
            contenido = m.group(1).rstrip()
            if _RE_FENCE.search(contenido):
                en_fenced = not en_fenced
                continue
            if en_fenced and _RE_BAD.search(contenido):
                out.append((ruta, i,
                            'ejemplo rustdoc usa `.unwrap()` o `try!()` '
                            'en vez de `?`'))
        else:
            en_fenced = False
    return out


def check_question_mark(fuentes, opts):
    """C-QUESTION-MARK: los ejemplos rustdoc usan `?`, no `try!()`,
    no `.unwrap()`."""
    out = []
    for ruta, texto in fuentes['rust']:
        out.extend(_doc_violations(ruta, texto))
    return out


# ===========================================================================
# Registro
# ===========================================================================

RULES = {
    'getter': (check_getter, 'C-GETTER: los getters por valor no usan prefijo get_'),
    'common-traits': (check_common_traits,
                      'C-COMMON-TRAITS: tipos publicos implementan Debug'),
    'question-mark': (check_question_mark,
                      'C-QUESTION-MARK: ejemplos rustdoc usan ? no try!/unwrap'),
}

# No hay aliases en la familia rust; los nombres de regla son los
# identificadores canonicos (resolver directamente por --rule).
ALIASES = {}


# ===========================================================================
# CLI
# ===========================================================================

def _formatear(lineas):
    return '\n'.join('{}:{}: {}'.format(
        os.path.basename(ruta), linea, detalle)
        for ruta, linea, detalle in lineas)


def main(argv=None):
    """Corre la regla pedida sobre el proyecto dado y devuelve el exit code."""
    ap = argparse.ArgumentParser(
        description='Instrumento de texto para Rust API Guidelines')
    ap.add_argument('--rule', help='Regla a evaluar')
    ap.add_argument('--list', action='store_true',
                    help='Lista las reglas disponibles')
    ap.add_argument('--proyecto', default=None,
                    help='Directorio del proyecto a inspeccionar')
    ap.add_argument('target', nargs='?', default=None,
                    help='Ruta objetivo (derive --proyecto de su directorio)')
    args = ap.parse_args(argv)

    if args.list:
        print(', '.join(sorted(RULES)))
        return 0

    if args.rule is None:
        print('INSTRUMENTO ROJO: falta --rule', file=sys.stderr)
        return 1

    if args.rule not in RULES:
        print('INSTRUMENTO ROJO: regla desconocida {}'.format(args.rule),
              file=sys.stderr)
        return 1

    if args.target is not None:
        if args.proyecto is None:
            args.proyecto = os.path.dirname(os.path.abspath(args.target))
    if args.proyecto is None:
        print('INSTRUMENTO ROJO: falta --proyecto/target', file=sys.stderr)
        return 1

    try:
        fuentes = _fuentes(args.proyecto)
    except NoVerificable as exc:
        print('NO-VERIFICABLE: {}'.format(exc), file=sys.stderr)
        return 2

    check, etiqueta = RULES[args.rule]
    lineas = check(fuentes, args)

    if lineas:
        print('INSTRUMENTO ROJO: {}'.format(etiqueta))
        print(_formatear(lineas))
        return 1

    print('OK: {}'.format(etiqueta))
    return 0


if __name__ == '__main__':
    sys.exit(main())
