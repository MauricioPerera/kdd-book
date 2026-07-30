#!/usr/bin/env python3
"""Instrumentos que miden sobre el historial de git.

Tres heuristicas de Scrum y eXtreme Programming hablan de propiedades que no
viven en un archivo ni en el tablero, sino en el historial del repositorio:
cada cuanto se entrega, si el codigo esta integrado en un solo lugar, y si el
test se escribio antes que la implementacion.

Siguen siendo `instrumented`, y esa es la razon de que valga la pena medirlas
aca: **git no lo llena nadie a mano**. Las fechas de los commits y de los tags
las pone la herramienta. Es la diferencia con el tablero, que tiene timestamps
automaticos pero contenido escrito por personas.

El caso del ciclo TDD merece decirse: "escribir el test y hacer que falle" es
una propiedad del *proceso*, y el estado final del codigo no la conserva. El
historial si: si el archivo de pruebas entro en un commit anterior o igual al
de la implementacion, el orden se cumplio. Es lo unico verificable despues de
los hechos, y conviene no confundirlo con haber visto el test en rojo.

Solo stdlib. Usa `subprocess` para hablar con git, por la misma razon que
repo_checks: para medir si algo paso, hay que preguntarselo a quien lo sabe.

Exit codes (convencion KDD):
  0  la propiedad se cumple
  1  no se cumple
  2  no se pudo verificar (sin git, sin repositorio, sin historial suficiente)

Uso:
    python git_checks.py --rule cadencia --max-dias 60 <ruta_del_repo>
    python git_checks.py --list
"""

import argparse
import datetime
import os
import subprocess
import sys


def _git(repo, *args):
    """Corre git en `repo`. Devuelve (codigo, stdout)."""
    proc = subprocess.run(['git'] + list(args), cwd=repo,
                          capture_output=True, text=True, timeout=60)
    return proc.returncode, proc.stdout.strip()


def _es_repo(repo):
    codigo, salida = _git(repo, 'rev-parse', '--is-inside-work-tree')
    return codigo == 0 and salida == 'true'


def check_cadencia(repo, opts):
    """Entregas cortas: el hueco entre entregas no puede pasar del maximo.

    Se leen los tags, que son lo que el equipo marca como entrega. Si no hay al
    menos dos, no hay cadencia que medir y se avisa en vez de dar verde.
    """
    codigo, salida = _git(repo, 'for-each-ref', '--sort=creatordate',
                          '--format=%(creatordate:short) %(refname:short)',
                          'refs/tags')
    if codigo != 0:
        return [('no se pudieron leer los tags', True)]
    lineas = [l for l in salida.splitlines() if l.strip()]
    if len(lineas) < 2:
        return [('hay {} tag(s) de entrega: hacen falta al menos dos para medir '
                 'una cadencia'.format(len(lineas)), True)]

    fechas = []
    for linea in lineas:
        crudo, _, nombre = linea.partition(' ')
        try:
            fechas.append((datetime.date.fromisoformat(crudo), nombre))
        except ValueError:
            return [('fecha de tag ilegible: {!r}'.format(linea), True)]

    out = []
    for (antes, n1), (despues, n2) in zip(fechas, fechas[1:]):
        dias = (despues - antes).days
        if dias > opts.max_dias:
            out.append(('entre {} y {} pasaron {} dias, el maximo es {}'
                        .format(n1, n2, dias, opts.max_dias), False))
    return out


def check_repounico(repo, opts):
    """Unificacion del codigo: nada quedandose fuera de la rama de integracion.

    Marca cada rama local que tenga commits que la rama de integracion no
    contiene. Una rama que diverge sin integrarse es codigo que el equipo cree
    tener y no tiene.
    """
    codigo, salida = _git(repo, 'rev-parse', '--verify', opts.rama)
    if codigo != 0:
        return [('no existe la rama de integracion {!r}'.format(opts.rama), True)]

    codigo, salida = _git(repo, 'for-each-ref', '--format=%(refname:short)',
                          'refs/heads')
    if codigo != 0:
        return [('no se pudieron listar las ramas', True)]

    out = []
    for rama in salida.splitlines():
        rama = rama.strip()
        if not rama or rama == opts.rama:
            continue
        codigo, pendientes = _git(repo, 'rev-list', '--count',
                                  '{}..{}'.format(opts.rama, rama))
        if codigo == 0 and pendientes.isdigit() and int(pendientes) > 0:
            out.append(('la rama {!r} tiene {} commit(s) sin integrar en {!r}'
                        .format(rama, pendientes, opts.rama), False))
    return out


def check_tddorden(repo, opts):
    """Ciclo TDD: el archivo de pruebas no puede entrar despues que el codigo.

    Verifica el orden de aparicion en el historial, que es lo unico que queda
    del proceso una vez terminado. No prueba que alguien haya visto el test en
    rojo; prueba que el test no se escribio al final para tapar el hueco.
    """
    if not opts.tests or not opts.codigo:
        return [('hacen falta --tests y --codigo para comparar su orden', True)]

    fechas = {}
    for etiqueta, ruta in (('tests', opts.tests), ('codigo', opts.codigo)):
        codigo, salida = _git(repo, 'log', '--diff-filter=A', '--format=%ct',
                              '--', ruta)
        if codigo != 0:
            return [('no se pudo leer el historial de {}'.format(ruta), True)]
        marcas = [int(x) for x in salida.split() if x.isdigit()]
        if not marcas:
            return [('{!r} no aparece en el historial: no se puede comparar el '
                     'orden'.format(ruta), True)]
        fechas[etiqueta] = min(marcas)

    if fechas['tests'] > fechas['codigo']:
        return [('las pruebas ({}) entraron despues que la implementacion ({}): '
                 'el ciclo no empezo por el test'
                 .format(opts.tests, opts.codigo), False)]
    return []


RULES = {
    'cadencia': (check_cadencia, 'Entregas cortas: hueco maximo entre entregas'),
    'repounico': (check_repounico, 'Unificacion del codigo en un repositorio'),
    'tddorden': (check_tddorden, 'Ciclo TDD: el test entra antes que el codigo'),
}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--rule')
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--max-dias', type=int, default=60)
    parser.add_argument('--rama', default='master')
    parser.add_argument('--tests')
    parser.add_argument('--codigo')
    parser.add_argument('repo', nargs='?', default='.')
    args = parser.parse_args(argv)

    if args.list:
        for nombre in sorted(RULES):
            print('{:11} {}'.format(nombre, RULES[nombre][1]))
        return 0

    if args.rule not in RULES:
        print('NO-VERIFICABLE: regla desconocida: {!r} (ver --list)'.format(args.rule))
        return 2
    if not os.path.isdir(args.repo):
        print('NO-VERIFICABLE: no existe el directorio: {}'.format(args.repo))
        return 2
    try:
        if not _es_repo(args.repo):
            print('NO-VERIFICABLE: {} no es un repositorio git'.format(args.repo))
            return 2
    except (OSError, subprocess.TimeoutExpired) as exc:
        print('NO-VERIFICABLE: no se pudo hablar con git: {}'.format(exc))
        return 2

    func, etiqueta = RULES[args.rule]
    try:
        hallazgos = func(args.repo, args)
    except (OSError, subprocess.TimeoutExpired) as exc:
        print('NO-VERIFICABLE: {}: {}'.format(etiqueta, exc))
        return 2

    no_verificables = [m for m, fatal in hallazgos if fatal]
    if no_verificables:
        print('NO-VERIFICABLE: {}'.format(etiqueta))
        for mensaje in no_verificables:
            print('  {}'.format(mensaje))
        return 2
    if hallazgos:
        print('INSTRUMENTO ROJO: {}'.format(etiqueta))
        for mensaje, _ in hallazgos:
            print('  {}'.format(mensaje))
        return 1

    print('OK: {}'.format(etiqueta))
    return 0


if __name__ == '__main__':
    sys.exit(main())
