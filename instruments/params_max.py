#!/usr/bin/env python3
"""Instrumento: cantidad maxima de parametros por funcion.

Mide la heuristica F1 de Codigo Limpio, la unica del catalogo cuyo umbral da el
propio autor: "Mas de tres ya es cuestionable y deberia evitarse".

Existe en version local ademas de `budget.params_max` porque el budget solo lo
aplica el gate de nivel 2 (MCP). Sin gate, el budget queda declarativo y el
contrato no se puede verificar solo. Con este instrumento en el `test_command`,
si.

Exit codes (convencion KDD):
  0  ninguna funcion supera el maximo
  1  al menos una lo supera
  2  no se pudo verificar

Uso:
    python params_max.py --max 3 <archivo.py> [<archivo.py> ...]
"""

import argparse
import ast
import sys


def count_params(func):
    """Parametros declarados, sin contar `self` ni `cls`."""
    spec = func.args
    names = [a.arg for a in spec.posonlyargs + spec.args + spec.kwonlyargs]
    if names and names[0] in ('self', 'cls'):
        names = names[1:]
    total = len(names)
    if spec.vararg:
        total += 1
    if spec.kwarg:
        total += 1
    return total


def measure(path):
    """Devuelve [(linea, nombre, n_params)] de cada funcion del archivo."""
    with open(path, 'r', encoding='utf-8') as fh:
        tree = ast.parse(fh.read(), filename=path)
    found = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            found.append((node.lineno, node.name, count_params(node)))
    return sorted(found)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--max', type=int, required=True)
    parser.add_argument('files', nargs='+')
    args = parser.parse_args(argv)

    violations = []
    for path in args.files:
        try:
            for lineno, name, count in measure(path):
                if count > args.max:
                    violations.append((path, lineno, name, count))
        except (OSError, SyntaxError) as exc:
            print('NO-VERIFICABLE: {}: {}'.format(path, exc))
            return 2

    if violations:
        print('INSTRUMENTO ROJO: params_max={}'.format(args.max))
        for path, lineno, name, count in violations:
            print('  {}:{}: {}() recibe {} parametros'.format(path, lineno, name, count))
        return 1

    print('OK: ninguna funcion supera params_max={}'.format(args.max))
    return 0


if __name__ == '__main__':
    sys.exit(main())
