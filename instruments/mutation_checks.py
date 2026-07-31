#!/usr/bin/env python3
"""Instrumento de mutacion de limites (G3 y T5 de Codigo Limpio).

G3 dice "comportamiento incorrecto en los limites" y T5 "probar condiciones de
limite". Las dos son la misma exigencia mirada desde lados opuestos: que la
suite se entere si un limite se corre un lugar.

Eso no se puede verificar leyendo el codigo ni leyendo los tests. Hay que
**romper el limite a proposito y ver si la suite lo nota**. Un mutante que
sobrevive es una condicion de limite que nadie esta probando.

Mutaciones que genera, todas sobre limites y ninguna sobre otra cosa:

    <  <->  <=        ==  ->  !=        n  ->  n+1
    >  <->  >=        !=  ->  ==        n  ->  n-1

Solo stdlib. Usa `subprocess` para correr la suite por cada mutante, por la
misma razon que los demas instrumentos que ejecutan: para saber si algo falla,
hay que hacerlo fallar.

Exit codes (convencion KDD):
  0  todos los mutantes murieron: la suite cubre los limites
  1  sobrevivio al menos uno: hay un limite sin probar
  2  no se pudo verificar (sin pruebas, o la suite ya estaba en rojo)

Uso:
    python mutation_checks.py --rule limites --proyecto proyecto <archivo.py>
"""

__all__ = ['NoVerificable', 'check_limites', 'main']

import argparse
import ast
import copy
import os
import subprocess
import sys

# Sobre que mide esta familia: el proyecto entero: manifiesto, punto de entrada o suite.
#
# Lo declara cada familia y no una lista en `memoria.py`, porque esa lista
# ya quedo vieja dos veces. `aplicar` elige por este campo que instrumentos
# puede correr sobre lo que le dieron; sin el, agregar una familia la deja
# afuera en silencio y nada falla.
ARTEFACTO = 'proyecto'

TIMEOUT = 120

# Cada operador de comparacion y su version corrida un lugar.
CORRIMIENTOS = {
    ast.Lt: ast.LtE, ast.LtE: ast.Lt,
    ast.Gt: ast.GtE, ast.GtE: ast.Gt,
    ast.Eq: ast.NotEq, ast.NotEq: ast.Eq,
}


class NoVerificable(Exception):
    """No hay con que medir: sin pruebas, o la suite ya venia en rojo."""


def _correr_suite(proyecto):
    proc = subprocess.run([sys.executable, '-m', 'unittest', 'discover',
                           '-s', '.', '-p', 'test_*.py', '-t', '.'],
                          cwd=proyecto, capture_output=True, text=True,
                          timeout=TIMEOUT)
    return proc.returncode, (proc.stdout or '') + (proc.stderr or '')


def _mutantes(arbol):
    """[(descripcion, arbol_mutado)] con una sola mutacion de limite cada uno."""
    out = []
    for indice, node in enumerate(ast.walk(arbol)):
        if isinstance(node, ast.Compare):
            for pos, op in enumerate(node.ops):
                reemplazo = CORRIMIENTOS.get(type(op))
                if reemplazo is None:
                    continue
                copia = copy.deepcopy(arbol)
                objetivo = list(ast.walk(copia))[indice]
                objetivo.ops[pos] = reemplazo()
                out.append(('linea {}: {} -> {}'.format(
                    getattr(node, 'lineno', '?'), type(op).__name__,
                    reemplazo.__name__), copia))
        elif isinstance(node, ast.Constant) and isinstance(node.value, int) \
                and not isinstance(node.value, bool):
            for delta in (1, -1):
                copia = copy.deepcopy(arbol)
                objetivo = list(ast.walk(copia))[indice]
                objetivo.value = node.value + delta
                out.append(('linea {}: {} -> {}'.format(
                    getattr(node, 'lineno', '?'), node.value, node.value + delta),
                    copia))
    return out


def check_limites(objetivo, proyecto, opts):
    """Muta los limites del archivo y exige que la suite mate a cada mutante."""
    with open(objetivo, 'r', encoding='utf-8') as fh:
        original = fh.read()
    arbol = ast.parse(original, filename=objetivo)

    codigo, salida = _correr_suite(proyecto)
    if codigo != 0:
        raise NoVerificable(
            'la suite ya esta en rojo antes de mutar nada: no se puede saber si '
            'mata a los mutantes\n{}'.format(salida.strip()[:300]))
    if 'Ran 0 tests' in salida:
        raise NoVerificable('la suite no corrio ninguna prueba')

    mutantes = _mutantes(arbol)
    if not mutantes:
        raise NoVerificable(
            'el archivo no tiene comparaciones ni enteros: no hay limite que mutar')

    sobrevivientes = []
    try:
        for descripcion, mutado in mutantes:
            with open(objetivo, 'w', encoding='utf-8', newline='\n') as fh:
                fh.write(ast.unparse(mutado) + '\n')
            codigo, _ = _correr_suite(proyecto)
            if codigo == 0:
                sobrevivientes.append(descripcion)
    finally:
        with open(objetivo, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(original)

    return sobrevivientes, len(mutantes)


RULES = {
    'limites': (check_limites, 'G3/T5 condiciones de limite: mutantes que la suite no mata'),
}


def main(argv=None):
    """Corre la regla pedida sobre los archivos dados y devuelve el exit
    code.
    """
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--rule')
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--proyecto')
    # El archivo a mutar se declara aparte del positional a proposito: en un
    # contrato, lo que se edita es el archivo de PRUEBAS y lo que hay que mutar
    # es el CODIGO. Son distintos, y confundirlos mutaria los tests.
    parser.add_argument('--mutar')
    parser.add_argument('objetivo', nargs='?')
    args = parser.parse_args(argv)
    if args.mutar:
        args.objetivo = args.mutar

    if args.list:
        for nombre in sorted(RULES):
            print('{:9} {}'.format(nombre, RULES[nombre][1]))
        return 0

    if args.rule not in RULES:
        print('NO-VERIFICABLE: regla desconocida: {!r} (ver --list)'.format(args.rule))
        return 2
    if not args.objetivo or not os.path.isfile(args.objetivo):
        print('NO-VERIFICABLE: no existe el archivo a mutar: {}'.format(args.objetivo))
        return 2
    proyecto = args.proyecto or os.path.dirname(os.path.abspath(args.objetivo))
    if not os.path.isdir(proyecto):
        print('NO-VERIFICABLE: no existe el proyecto: {}'.format(proyecto))
        return 2

    func, etiqueta = RULES[args.rule]
    try:
        sobrevivientes, total = func(args.objetivo, proyecto, args)
    except NoVerificable as exc:
        print('NO-VERIFICABLE: {}: {}'.format(etiqueta, exc))
        return 2
    except (OSError, SyntaxError, subprocess.TimeoutExpired) as exc:
        print('NO-VERIFICABLE: {}: {}'.format(etiqueta, exc))
        return 2

    if sobrevivientes:
        print('INSTRUMENTO ROJO: {} ({} de {} mutantes sobrevivieron)'.format(
            etiqueta, len(sobrevivientes), total))
        for descripcion in sobrevivientes:
            print('  sobrevivio: {}'.format(descripcion))
        print('  Cada sobreviviente es un limite que se puede correr un lugar sin '
              'que ninguna prueba se entere.')
        return 1

    print('OK: {} ({} mutantes, todos muertos)'.format(etiqueta, total))
    return 0


if __name__ == '__main__':
    sys.exit(main())
