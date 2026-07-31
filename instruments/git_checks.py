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

# Sobre que mide esta familia: el historial de un repositorio.
#
# Lo declara cada familia y no una lista en `memoria.py`, porque esa lista
# ya quedo vieja dos veces. `aplicar` elige por este campo que instrumentos
# puede correr sobre lo que le dieron; sin el, agregar una familia la deja
# afuera en silencio y nada falla.
ARTEFACTO = 'repositorio-git'


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
    lineas = [x for x in salida.splitlines() if x.strip()]
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


def check_codebase(repo, opts):
    """Un codebase por aplicacion, bajo control de versiones.

    Es la unica regla del modulo para la que **no ser un repositorio es el
    hallazgo y no una imposibilidad**. Las otras tres miden propiedades DEL
    historial, asi que sin historial no hay nada que medir y sale exit 2; esta
    mide si hay historial, y ahi "no lo hay" es exactamente el rojo. Por eso
    `main` se saltea la comprobacion previa para ella.

    La segunda mitad —un solo codebase— se mide contando repositorios anidados.
    Que haya otro `.git` adentro significa que en el arbol conviven dos
    codebases, que es la forma en que el factor dice que se rompe.

    Lo que no puede ver: si OTRO repositorio comparte este codigo. Eso pasa
    afuera del artefacto y ninguna lectura de este arbol lo alcanza.
    """
    if not _es_repo(repo):
        return [('el proyecto no esta bajo control de versiones: sin eso no hay '
                 'codebase del que hablar', False)]

    anidados = []
    for raiz, dirs, _archivos in os.walk(repo):
        if os.path.abspath(raiz) == os.path.abspath(repo):
            continue
        if '.git' in dirs:
            anidados.append(os.path.relpath(raiz, repo))
        dirs[:] = [d for d in dirs if d != '.git']

    out = [('{} es otro codebase dentro de este: dos codebases no son una '
            'aplicacion, son un sistema distribuido'.format(ruta), False)
           for ruta in sorted(anidados)]
    return out


def check_releaseid(repo, opts):
    """Todo release tiene un identificador propio.

    El autor lo pide literal —"every release should always have a unique release
    ID"— y de eso quedan dos rastros medibles en el historial. Que no haya
    ninguna marca de release es el primero. Que dos marcas apunten al mismo
    commit es el segundo, y es el mas util: si dos identificadores nombran el
    mismo estado, el identificador no esta identificando el release.

    Que git impida repetir el NOMBRE de un tag no ahorra esta regla: lo que se
    repite en la practica no es el nombre sino el estado.
    """
    codigo, salida = _git(repo, 'for-each-ref', '--format=%(refname:short) %(objectname)',
                          'refs/tags')
    if codigo != 0:
        return [('no se pudieron leer los tags', True)]

    lineas = [x for x in salida.splitlines() if x.strip()]
    if not lineas:
        return [('no hay ninguna marca de release: ningun release tiene '
                 'identificador', False)]

    por_commit = {}
    for linea in lineas:
        nombre, _, objeto = linea.partition(' ')
        # Un tag anotado apunta a un objeto tag, no al commit: se desreferencia
        # para comparar estados y no envoltorios.
        _c, commit = _git(repo, 'rev-list', '-n', '1', nombre)
        por_commit.setdefault(commit or objeto, []).append(nombre)

    return [('{} nombran el mismo estado ({}): dos identificadores para un '
             'release'.format(', '.join(sorted(nombres)), commit[:8]), False)
            for commit, nombres in sorted(por_commit.items()) if len(nombres) > 1]


RULES = {
    'cadencia': (check_cadencia, 'Entregas cortas: hueco maximo entre entregas'),
    'codebase': (check_codebase, 'Codebase: uno por aplicacion, bajo control de versiones'),
    'releaseid': (check_releaseid, 'Release: todo release tiene identificador propio'),
    'repounico': (check_repounico, 'Unificacion del codigo en un repositorio'),
    'tddorden': (check_tddorden, 'Ciclo TDD: el test entra antes que el codigo'),
}

# Reglas para las que la ausencia de repositorio ES el hallazgo, no una
# imposibilidad de medir. Sin esta lista, `codebase` saldria con exit 2 sobre un
# directorio sin control de versiones, que es justo el caso que tiene que
# marcar en rojo.
SIN_REPO_ES_HALLAZGO = ('codebase',)


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
        if args.rule not in SIN_REPO_ES_HALLAZGO and not _es_repo(args.repo):
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
