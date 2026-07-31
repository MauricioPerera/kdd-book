#!/usr/bin/env python3
"""Instrumentos que miden las dos prohibiciones planas de docs.stripe.com/api.

Familia nueva, y la mas chica del repositorio: dos reglas, una por cada
prohibicion sin condicional que trae la seccion "Using the API" de la
referencia de Stripe. El resto de esa seccion (Errors, Pagination,
Versioning, Request IDs) es forma del objeto de respuesta o de como cada SDK
fija version -referencia, no tecnica-, y Expanding responses es una
capacidad opcional sin correcto/incorrecto que exigir.

    claves-en-codigo       cero claves secretas o restringidas en literales
    idempotencia-en-lectura cero headers Idempotency-Key en GET o DELETE

**Lo que estas reglas no pueden ver, dicho de entrada.** No hay parser HTTP
real: se lee codigo Python via `ast`, igual que `entorno_checks`. Una clave
armada por concatenacion o interpolacion en tiempo de ejecucion no la ve
nadie -no es un string literal-, y un header de idempotencia puesto en una
variable intermedia en vez de un dict inline en la llamada tampoco. El
alcance esta escrito en cada `check_`, para que el verde no se lea como mas
de lo que es.

Exit codes (convencion KDD):
  0  la propiedad se cumple
  1  no se cumple
  2  no se pudo verificar (falta el dato, o no hay que medir)

Uso:
    python stripe_checks.py --rule claves-en-codigo <entrada.py>
    python stripe_checks.py --rule idempotencia-en-lectura <entrada.py>
    python stripe_checks.py --list
"""

__all__ = [
    'NoVerificable',
    'check_claves_en_codigo',
    'check_idempotencia_en_lectura',
    'main',
]

import argparse
import ast
import os
import re
import sys

# Sobre que mide esta familia: el proyecto entero (todo .py que no sea prueba).
ARTEFACTO = 'proyecto'


class NoVerificable(Exception):
    """Falta el dato sin el cual la regla no se puede evaluar (exit 2)."""


# Claves secretas (`sk_`) y restringidas (`rk_`), en modo test o live. Las
# publicables (`pk_`) quedan afuera a proposito: la propia pagina de
# Authentication las trata como hechas para vivir en el cliente, asi que
# encontrarlas en el codigo no es la violacion que describe esta regla.
_CLAVE = re.compile(r'\b(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{10,}\b')

# Llamadas que representan un metodo HTTP. El nombre del atributo alcanza
# para reconocer `requests.get(...)`, `session.post(...)`, `client.delete(...)`:
# no hace falta saber que libreria es, porque las tres comparten el verbo
# como nombre de metodo.
_METODOS_LECTURA = ('get', 'delete')
_METODOS_HTTP = ('get', 'post', 'put', 'patch', 'delete')


def _fuentes(proyecto):
    """(ruta, arbol, texto) de cada .py del proyecto que no sea prueba."""
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


def _todos_los_strings(arbol):
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str):
            yield nodo.lineno, nodo.value


def _nombre_llamado(nodo):
    """El nombre invocado en un Call, sin el receptor: `s.get(...)` -> `get`."""
    func = nodo.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return ''


def _headers_inline(nodo):
    """El dict literal del kwarg `headers=` de un Call, o None si no hay.

    Solo lee un dict literal escrito ahi mismo. Un `headers=mis_headers`
    armado antes en una variable no se sigue -es el limite declarado del
    modulo, igual que `entorno_checks` con los literales asignados-.
    """
    for kw in nodo.keywords:
        if kw.arg == 'headers' and isinstance(kw.value, ast.Dict):
            return kw.value
    return None


def _claves_del_dict(nodo_dict):
    """Los nombres de clave literales de un ast.Dict, en minuscula."""
    out = []
    for k in nodo_dict.keys:
        if isinstance(k, ast.Constant) and isinstance(k.value, str):
            out.append(k.value.lower())
    return out


def check_claves_en_codigo(fuentes, opts):
    """Cero claves secretas o restringidas de Stripe escritas como literal.

    Authentication lo dice sin condicional: "Don't embed secret or restricted
    API keys in source code or client-side applications." La prohibicion es
    plana, asi que el umbral es cero sin discusion, igual que `config` en
    `entorno_checks` con cualquier otra credencial.

    Alcance: reconoce la clave por su forma (`sk_`/`rk_` + modo + cuerpo), no
    por el nombre de la variable donde vive -asi la ve tanto en una
    asignacion como en un argumento inline-. Las claves publicables (`pk_`)
    no cuentan: la misma pagina las trata como pensadas para el cliente.
    """
    out = []
    for archivo, arbol, _texto in fuentes:
        for linea, valor in _todos_los_strings(arbol):
            m = _CLAVE.search(valor)
            if m:
                out.append((archivo, linea,
                            '{!r} es una clave secreta o restringida de Stripe '
                            'embebida en el codigo fuente'.format(m.group(0))))
    return out


def check_idempotencia_en_lectura(fuentes, opts):
    """Cero headers Idempotency-Key en peticiones GET o DELETE.

    Idempotent requests lo dice sin condicional: "Don't send idempotency keys
    in GET and DELETE requests because it has no effect." La otra mitad de
    esa pagina -usar una clave de idempotencia al crear o actualizar- es
    condicional ("cuando..."), y por eso no entra en el umbral: exigirla en
    cada POST seria inventar una regla que el texto no da sin condicion.

    Alcance: solo ve un `headers={...}` escrito inline en la llamada, y solo
    reconoce el metodo por el nombre del atributo invocado (`get`, `delete`).
    Un GET hecho con otra forma -sesion reusada, wrapper propio- no lo ve.
    """
    out = []
    for archivo, arbol, _texto in fuentes:
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, ast.Call):
                continue
            metodo = _nombre_llamado(nodo)
            if metodo not in _METODOS_LECTURA:
                continue
            headers = _headers_inline(nodo)
            if headers is None:
                continue
            if 'idempotency-key' in _claves_del_dict(headers):
                out.append((archivo, nodo.lineno,
                            '{}(...) con Idempotency-Key: no tiene efecto en '
                            'peticiones {}'.format(metodo, metodo.upper())))
    return out


RULES = {
    'claves-en-codigo': (check_claves_en_codigo,
                         'Authentication: cero claves secretas o restringidas en el codigo'),
    'idempotencia-en-lectura': (check_idempotencia_en_lectura,
                                'Idempotent requests: cero Idempotency-Key en GET o DELETE'),
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
