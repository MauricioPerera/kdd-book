#!/usr/bin/env python3
"""Instrumentos de nivel repo para Codigo Limpio (E1, E2, G24, T1, T2, T9).

Estas seis heuristicas no hablan de un archivo sino del proyecto: cuantos pasos
hace falta para generar, para probar, si hay cobertura, cuanto tarda la suite,
si se siguen las convenciones. El `target` deja de ser codigo a refactorizar y
pasa a ser el **punto de entrada** del proyecto.

Siguen siendo `instrumented`: nadie las declara a mano. El instrumento ejecuta
el comando y mide el resultado. Por eso este modulo usa `subprocess`, igual que
`validate_test_commands.py` del repo KDD rompe su propia convencion de
`forbids: subprocess` por la misma razon: para medir si algo corre, hay que
correrlo.

Solo stdlib. La cobertura sale de `trace`, no de una dependencia externa.

Exit codes (convencion KDD):
  0  la propiedad se cumple
  1  no se cumple
  2  no se pudo verificar

Uso:
    python repo_checks.py --rule e2 --min-tests 3 <punto_de_entrada.py>
    python repo_checks.py --list
"""

import argparse
import ast
import io
import os
import re
import subprocess
import sys
import time
import trace as trace_mod


TIMEOUT = 120


def _entry(target):
    """(directorio del proyecto, nombre del punto de entrada)."""
    return os.path.dirname(os.path.abspath(target)), os.path.basename(target)


def _run(target, task):
    project, entry = _entry(target)
    started = time.monotonic()
    proc = subprocess.run([sys.executable, entry, task], cwd=project,
                          capture_output=True, text=True, timeout=TIMEOUT)
    return proc, time.monotonic() - started


def _sources(project):
    """Archivos .py del proyecto que no son tests ni el punto de entrada."""
    out = []
    for root, _dirs, files in os.walk(project):
        for name in sorted(files):
            if name.endswith('.py') and not name.startswith('test_') \
                    and name not in ('tareas.py', '__init__.py'):
                out.append(os.path.join(root, name))
    return sorted(out)


def _is_docstring(node):
    """True si el nodo es un docstring.

    Python los guarda en `__doc__` al compilar y no los ejecuta como sentencia,
    asi que `trace` nunca los ve. Contarlos como ejecutables castiga al codigo
    documentado: una medicion de cobertura que baja cuando agregas docstrings
    esta midiendo mal.
    """
    return (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str))


def _statement_lines(path):
    """Lineas con sentencia ejecutable, segun el AST."""
    with open(path, 'r', encoding='utf-8') as fh:
        tree = ast.parse(fh.read(), filename=path)
    docstrings = set()
    for holder in ast.walk(tree):
        body = getattr(holder, 'body', None)
        if isinstance(body, list) and body and _is_docstring(body[0]):
            docstrings.add(body[0].lineno)
    lines = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.stmt) and not isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.lineno not in docstrings:
                lines.add(node.lineno)
    return lines


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_e1(target, opts):
    """E1: generar debe requerir un solo paso."""
    try:
        proc, _ = _run(target, 'build')
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [('no se pudo ejecutar el paso de generacion: {}'.format(exc), True)]
    if proc.returncode != 0:
        return [('`{} build` termino en {}; generar todavia necesita pasos manuales:\n{}'
                 .format(os.path.basename(target), proc.returncode,
                         (proc.stderr or proc.stdout).strip()[:400]), False)]
    return []


def check_e2(target, opts):
    """E2: probar debe requerir un solo paso, y ese paso debe correr los tests."""
    try:
        proc, _ = _run(target, 'test')
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [('no se pudo ejecutar el paso de pruebas: {}'.format(exc), True)]
    salida = (proc.stdout or '') + (proc.stderr or '')
    if proc.returncode != 0:
        return [('`{} test` termino en {}; probar todavia necesita pasos manuales:\n{}'
                 .format(os.path.basename(target), proc.returncode,
                         salida.strip()[:400]), False)]
    match = re.search(r'Ran (\d+) tests?', salida)
    if not match:
        return [('`{} test` no reporta cuantas pruebas corrio: un comando unico que '
                 'no prueba nada tambien sale 0'.format(os.path.basename(target)), False)]
    corridos = int(match.group(1))
    if corridos < opts.min_tests:
        return [('el paso unico corrio {} prueba(s), se exigen {}'
                 .format(corridos, opts.min_tests), False)]
    return []


def check_t9(target, opts):
    """T9: la suite debe ser rapida."""
    try:
        proc, elapsed = _run(target, 'test')
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [('no se pudo cronometrar la suite: {}'.format(exc), True)]
    if proc.returncode != 0:
        return [('la suite no termina en verde, no tiene sentido cronometrarla', True)]
    if elapsed > opts.max_seconds:
        return [('la suite tardo {:.2f}s, el maximo es {:.2f}s'
                 .format(elapsed, opts.max_seconds), False)]
    return []


def _coverage(target):
    """(lineas cubiertas, lineas ejecutables) del proyecto, con stdlib `trace`."""
    project, entry = _entry(target)
    tracer = trace_mod.Trace(count=1, trace=0, ignoredirs=[sys.prefix, sys.exec_prefix])
    saved_path, saved_argv = list(sys.path), list(sys.argv)
    saved_stdout = sys.stdout
    # Los modulos que importe el descubrimiento quedan cacheados en
    # sys.modules. Sin limpiarlos, medir un segundo proyecto que tenga un
    # archivo con el mismo nombre reusa el del primero y unittest aborta. Es
    # un fallo real del instrumento, no solo de las pruebas: t1 y t2 miden los
    # dos y correrian en el mismo proceso.
    saved_modules = set(sys.modules)
    sys.path.insert(0, project)
    sys.argv = [entry, 'test']
    sys.stdout = io.StringIO()
    try:
        tracer.runfunc(_discover_and_run, project)
    finally:
        sys.stdout = saved_stdout
        sys.path, sys.argv = saved_path, saved_argv
        for nombre in set(sys.modules) - saved_modules:
            sys.modules.pop(nombre, None)

    ejecutadas = {(os.path.abspath(f), n) for (f, n) in tracer.results().counts}
    cubiertas = total = 0
    for path in _sources(project):
        lineas = _statement_lines(path)
        total += len(lineas)
        cubiertas += sum(1 for n in lineas if (os.path.abspath(path), n) in ejecutadas)
    return cubiertas, total


def _discover_and_run(project):
    import unittest
    suite = unittest.defaultTestLoader.discover(project, pattern='test_*.py',
                                                top_level_dir=project)
    unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)


def check_t2(target, opts):
    """T2: el proyecto debe exponer la medicion de cobertura como tarea propia.

    La version anterior media cobertura con su propio `trace` y daba verde si el
    numero salia. Eso verifica "la cobertura es medible", que no es lo que dice
    la heuristica: T2 pide que el equipo **use** una herramienta de cobertura, o
    sea que este disponible en el proyecto y no en la cabeza de quien la corre.
    Por eso ahora se le pide al punto de entrada, no al instrumento.
    """
    try:
        proc, _ = _run(target, 'coverage')
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [('no se pudo ejecutar la tarea de cobertura: {}'.format(exc), True)]
    salida = (proc.stdout or '') + (proc.stderr or '')
    if proc.returncode != 0:
        return [('`{} coverage` termino en {}: el proyecto no expone la medicion '
                 'como tarea propia'.format(os.path.basename(target),
                                            proc.returncode), False)]
    if not re.search(r'\d+(\.\d+)?\s*%', salida):
        return [('`{} coverage` no reporta ningun porcentaje: una tarea que no '
                 'informa un numero no es una medicion'
                 .format(os.path.basename(target)), False)]
    return []


def check_t1(target, opts):
    """T1: pruebas insuficientes, medido como cobertura de linea."""
    try:
        cubiertas, total = _coverage(target)
    except Exception as exc:  # noqa: BLE001
        return [('no se pudo medir cobertura: {}'.format(exc), True)]
    if total == 0:
        return [('no hay lineas ejecutables que medir', True)]
    porcentaje = 100.0 * cubiertas / total
    if porcentaje < opts.min_coverage:
        return [('cobertura {:.1f}% ({}/{} lineas), el minimo es {:.1f}%'
                 .format(porcentaje, cubiertas, total, opts.min_coverage), False)]
    return []


def check_g24(target, opts):
    """G24: seguir las convenciones estandar.

    Subconjunto declarado y determinista, no un linter completo: largo de linea,
    tabuladores para indentar, espacios al final y salto de linea final. Se
    declara el subconjunto a proposito — decir "convenciones estandar" sin
    enumerarlas seria pedir algo no verificable.
    """
    project, _ = _entry(target)
    out = []
    for root, _dirs, files in os.walk(project):
        for name in sorted(files):
            if not name.endswith('.py'):
                continue
            path = os.path.join(root, name)
            rel = os.path.relpath(path, project)
            with open(path, 'r', encoding='utf-8', newline='') as fh:
                contenido = fh.read()
            if contenido and not contenido.endswith('\n'):
                out.append(('{}: no termina en salto de linea'.format(rel), False))
            for numero, linea in enumerate(contenido.splitlines(), start=1):
                if len(linea) > opts.max_line:
                    out.append(('{}:{}: linea de {} caracteres (max {})'
                                .format(rel, numero, len(linea), opts.max_line), False))
                if linea.startswith('\t'):
                    out.append(('{}:{}: indentacion con tabulador'.format(rel, numero), False))
                if linea.rstrip() != linea:
                    out.append(('{}:{}: espacios al final'.format(rel, numero), False))
    return out


def _ids_de_prueba(project):
    """Identificadores `modulo.Clase.metodo` de cada prueba del proyecto."""
    ids = []
    for nombre in sorted(os.listdir(project)):
        if not (nombre.startswith('test_') and nombre.endswith('.py')):
            continue
        with open(os.path.join(project, nombre), 'r', encoding='utf-8') as fh:
            arbol = ast.parse(fh.read(), filename=nombre)
        modulo = nombre[:-3]
        for clase in arbol.body:
            if not isinstance(clase, ast.ClassDef):
                continue
            for metodo in clase.body:
                if isinstance(metodo, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                        and metodo.name.startswith('test'):
                    ids.append('{}.{}.{}'.format(modulo, clase.name, metodo.name))
    return ids


def check_aislamiento(target, opts):
    """Las pruebas unitarias deben ser independientes entre si.

    Se corre **cada prueba por separado**, no cada modulo. La primera version
    aislaba modulos y no detectaba nada: una prueba que depende del estado que
    dejo su vecina de arriba pasa igual cuando el modulo corre entero, porque la
    vecina corre igual. Aislar de a modulo mide el acoplamiento entre archivos y
    deja pasar el que esta adentro, que es el mas comun.

    Si una prueba solo pasa acompanada, no es unitaria: el dia que cambie el
    orden va a fallar sin que nadie entienda por que.
    """
    project, _ = _entry(target)
    ids = _ids_de_prueba(project)
    if not ids:
        return [('no hay pruebas que aislar', True)]

    out = []
    for identificador in ids:
        try:
            proc = subprocess.run([sys.executable, '-m', 'unittest', identificador],
                                  cwd=project, capture_output=True, text=True,
                                  timeout=TIMEOUT)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return [('no se pudo correr {} por separado: {}'.format(identificador, exc), True)]
        if proc.returncode != 0:
            out.append(('{} no pasa corrida sola: depende de otra prueba'
                        .format(identificador), False))
    return out


RULES = {
    'aislamiento': (check_aislamiento, 'Pruebas unitarias independientes entre si'),
    'e1': (check_e1, 'E1 generar en un solo paso'),
    'e2': (check_e2, 'E2 probar en un solo paso'),
    'g24': (check_g24, 'G24 seguir las convenciones estandar (subconjunto declarado)'),
    't1': (check_t1, 'T1 pruebas suficientes (cobertura de linea)'),
    't2': (check_t2, 'T2 usar una herramienta de cobertura'),
    't9': (check_t9, 'T9 las pruebas deben ser rapidas'),
}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--rule')
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--min-tests', type=int, default=1)
    parser.add_argument('--max-seconds', type=float, default=5.0)
    parser.add_argument('--min-coverage', type=float, default=80.0)
    parser.add_argument('--max-line', type=int, default=100)
    parser.add_argument('files', nargs='*')
    args = parser.parse_args(argv)

    if args.list:
        for name in sorted(RULES):
            print('{:4} {}'.format(name, RULES[name][1]))
        return 0

    if args.rule not in RULES:
        print('NO-VERIFICABLE: regla desconocida: {!r} (ver --list)'.format(args.rule))
        return 2
    if len(args.files) != 1:
        print('NO-VERIFICABLE: se espera exactamente un punto de entrada')
        return 2
    target = args.files[0]
    if not os.path.isfile(target):
        print('NO-VERIFICABLE: no existe el punto de entrada: {}'.format(target))
        return 2

    func, label = RULES[args.rule]
    hallazgos = func(target, args)
    no_verificables = [m for m, fatal in hallazgos if fatal]
    if no_verificables:
        print('NO-VERIFICABLE: {}'.format(label))
        for mensaje in no_verificables:
            print('  {}'.format(mensaje))
        return 2
    if hallazgos:
        print('INSTRUMENTO ROJO: {}'.format(label))
        for mensaje, _ in hallazgos:
            print('  {}'.format(mensaje))
        return 1

    print('OK: {}'.format(label))
    return 0


if __name__ == '__main__':
    sys.exit(main())
