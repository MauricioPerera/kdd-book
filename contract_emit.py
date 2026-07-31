#!/usr/bin/env python3
"""Emisor determinista de contratos hibridos OKF+CCDD desde ejercicios de libro.

Fase 2 del pipeline. Toma los ejercicios (`spec.json` + seed + oraculo +
solucion) y produce un arbol que pasa a la vez:

  - `validate_okf.py`      (el contrato es un nodo OKF alcanzable y enlazado)
  - `validate_contracts.py` (frontmatter CCDD, secciones, sello del oraculo)
  - `validate_test_commands.py` (el `test_command` real termina en 0)

Dos restricciones del validador definen todo el diseno, y conviene tenerlas a
la vista porque no son obvias:

1. `budget` SOLO admite cyclomatic_max, nesting_max, lines_max y params_max.
   Son las cuatro metricas que lee el gate de nivel 2; cualquier otra subclave
   es un error porque el tope quedaria ignorado en silencio. De las 32
   heuristicas contractables de Codigo Limpio, casi ninguna mapea a esas
   cuatro. Las demas necesitan que la tecnica la lleve un instrumento propio
   dentro del `test_command`.

2. `test_command` se ejecuta con `shlex.split` + `subprocess.run` SIN shell,
   asi que no admite `&&`. Por eso el comando es un runner unico
   (`instruments/gate.py`) que corre oraculo e instrumento por separado.

Exit codes (convencion KDD):
  0  contratos emitidos
  1  error de contenido (nodo OKF inexistente, campo invalido, budget fuera de
     vocabulario)
  2  no se pudo verificar (spec ilegible, destino no escribible)

Uso:
    python contract_emit.py <dir_ejercicios> --out out --book codigo-limpio
"""

__all__ = ['EmitError', 'emit', 'load_specs', 'main']

import argparse
import hashlib
import json
import os
import shutil
import sys

BUDGET_KEYS = ('cyclomatic_max', 'nesting_max', 'lines_max', 'params_max')

# Un bloque POR LIBRO, igual que en okf_emit y por el mismo motivo: con un
# bloque compartido, emitir los contratos de un segundo libro borraba del
# indice los del primero y sus 26 contratos quedaban huerfanos.
INDEX_BEGIN = '<!-- contract-emit:libro:{} -->'
INDEX_END = '<!-- /contract-emit:libro:{} -->'

STOP_MARKER = 'PARAR y reportar si'


# Todo lo que es igual en cada ejercicio vive aca, no repetido 22 veces. Un
# spec solo declara lo que lo distingue: que tecnica mide y con que umbral.
DEFAULTS = {
    'target': 'target.py',
    'oracle': 'oracle_test.py',
    'seed': 'seed.py',
    'kind': 'refactor',
    'forbids': ['network', 'subprocess'],
    'deps_allowed': [],
    'budget': {'cyclomatic_max': 5, 'nesting_max': 2, 'lines_max': 60, 'params_max': 3},
}

# El oraculo esta sellado en todos los contratos, asi que la prohibicion de
# tocarlo y el corte por instrumento no-verificable no se escriben a mano.
DONT_SIEMPRE = 'Tocar el oraculo: esta congelado y su sha256 esta en el contrato.'
STOP_SIEMPRE = 'el instrumento reporta NO-VERIFICABLE (exit 2)'


class EmitError(Exception):
    """El spec describe un contrato invalido (exit 1)."""


def _con_defaults(spec, book):
    """Completa el spec con los valores comunes antes de validarlo."""
    full = dict(DEFAULTS)
    full.update({k: v for k, v in spec.items() if v is not None})
    full.setdefault('book', book)
    full.setdefault('task', full['id'].replace('-', '_'))
    full['dont'] = list(full.get('dont', [])) + [DONT_SIEMPRE]
    full['stop_if'] = list(full.get('stop_if', [])) + [STOP_SIEMPRE]
    return full


def _q(value):
    text = str(value).replace('\n', ' ').strip().replace("'", '’')
    return "'{}'".format(text)


def _seal(path):
    """SHA256 del oraculo con newlines normalizados a LF.

    Debe coincidir exactamente con `_calculate_tests_hash` de
    validate_contracts.py o el sello queda roto.
    """
    with open(path, 'r', encoding='utf-8') as fh:
        content = fh.read()
    normalized = content.replace('\r\n', '\n').replace('\r', '\n')
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def _check(spec, knowledge_dir, book):
    """Valida el spec antes de escribir. Lanza EmitError con el motivo."""
    for key in ('id', 'node', 'task', 'title', 'description', 'intent',
                'signature', 'instrument', 'budget'):
        if not spec.get(key):
            raise EmitError('{}: campo requerido ausente: {}'.format(
                spec.get('id', '?'), key))

    budget = spec['budget']
    if not isinstance(budget, dict) or not budget:
        raise EmitError('{}: budget debe ser un mapa no vacio'.format(spec['id']))
    for key, value in sorted(budget.items()):
        if key not in BUDGET_KEYS:
            raise EmitError(
                "{}: budget.{} no la lee el gate de nivel 2, el tope quedaria "
                "ignorado en silencio (validas: {})".format(
                    spec['id'], key, ', '.join(BUDGET_KEYS)))
        if not (isinstance(value, int) and not isinstance(value, bool) and value > 0):
            raise EmitError('{}: budget.{} debe ser entero positivo (es {!r})'.format(
                spec['id'], key, value))

    # El contrato enlaza al nodo OKF de la tecnica (regla 3: no duplicar
    # reglas, enlazarlas). Si el nodo no existe el enlace queda roto y
    # validate_okf.py lo rechaza, asi que se comprueba antes de escribir.
    node_path = os.path.join(knowledge_dir, book, spec['node'] + '.md')
    if not os.path.isfile(node_path):
        raise EmitError(
            "{}: el nodo OKF referenciado no existe: {} (corre antes la fase 1)"
            .format(spec['id'], os.path.relpath(node_path)))

    if len(spec.get('examples', [])) < 2:
        raise EmitError('{}: se requieren >=2 examples'.format(spec['id']))
    if not spec.get('stop_if'):
        raise EmitError('{}: se requiere al menos un stop_if'.format(spec['id']))


def _render(spec, book, rel_target, rel_tests, seal, exercise_rel):
    node_link = '../{}/{}.md'.format(book, spec['node'])
    lines = []
    lines.append('---')
    lines.append("type: 'Task Contract'")
    lines.append('title: {}'.format(_q(spec['title'])))
    lines.append('description: {}'.format(_q(spec['description'])))
    lines.append("tags: ['ccdd', 'derivado-de-libro', {}]".format(_q(book)))
    lines.append('')
    lines.append('task: {}'.format(spec['task']))
    lines.append('intent: {}'.format(_q(spec['intent'])))
    lines.append('target: {}'.format(rel_target))
    lines.append('signature: "{}"'.format(spec['signature']))
    lines.append('test_command: "python instruments/gate.py {}"'.format(exercise_rel))
    lines.append('budget:')
    for key in BUDGET_KEYS:
        if key in spec['budget']:
            lines.append('  {}: {}'.format(key, spec['budget'][key]))
    lines.append('tests: {}'.format(rel_tests))
    lines.append('tests_sha256: "{}"'.format(seal))
    lines.append("touch_only: ['{}']".format(rel_target))
    lines.append('deps_allowed: {}'.format(
        '[' + ', '.join(_q(d) for d in spec.get('deps_allowed', [])) + ']'))
    lines.append('forbids: {}'.format(
        '[' + ', '.join(_q(f) for f in spec.get('forbids', [])) + ']'))
    lines.append('---')
    lines.append('')
    lines.append('# {}'.format(spec['title']))
    lines.append('')

    lines.append('## Intent')
    lines.append('')
    lines.append(spec['intent'])
    lines.append('')
    lines.append('La regla de negocio no se repite aca: vive en '
                 '[{}]({}).'.format(spec['node'], node_link))
    lines.append('')

    lines.append('## Interface')
    lines.append('')
    lines.append('```python')
    lines.append(spec['signature'])
    lines.append('```')
    lines.append('')
    lines.append('Definida en `{}`. El oraculo la usa tal cual, asi que es parte '
                 'del contrato congelado.'.format(rel_target))
    lines.append('')

    lines.append('## Invariants')
    lines.append('')
    for item in spec.get('invariants', []):
        lines.append('- {}'.format(item))
    lines.append('')

    lines.append('## Examples')
    lines.append('')
    for item in spec['examples']:
        lines.append('- {}'.format(item))
    lines.append('')

    lines.append("## Do / Don't")
    lines.append('')
    lines.append('**Do:**')
    lines.append('')
    for item in spec.get('do', []):
        lines.append('- {}'.format(item))
    lines.append('')
    lines.append("**Don't:**")
    lines.append('')
    for item in spec.get('dont', []):
        lines.append('- {}'.format(item))
    lines.append('')

    lines.append('## Tests')
    lines.append('')
    lines.append('```')
    lines.append('python instruments/gate.py {}'.format(exercise_rel))
    lines.append('```')
    lines.append('')
    lines.append('El comando corre dos cosas distintas y las reporta por separado:')
    lines.append('')
    lines.append('1. **Oraculo** (`{}`, sellado en `tests_sha256`): no rompiste el '
                 'comportamiento.'.format(rel_tests))
    lines.append('2. **Instrumento** (`{}` con `{}`): aplicaste la tecnica.'.format(
        spec['instrument']['script'], spec['instrument'].get('threshold', '')))
    lines.append('')
    if spec.get('kind') == 'refactor':
        lines.append('Esta tecnica es una refactorizacion: por definicion no cambia el')
        lines.append('comportamiento observable, asi que **el oraculo esta verde antes de')
        lines.append('empezar y seguira verde si no haces nada**. Lo unico que discrimina')
        lines.append('si el trabajo se hizo es el instrumento. No alcanza con los tests.')
    else:
        lines.append('Esta tecnica cambia la interfaz, asi que el oraculo arranca en rojo.')
        lines.append('Aun asi el instrumento hace falta: sin el, nada impide satisfacer el')
        lines.append('oraculo con una firma que siga violando el umbral.')
    lines.append('')

    lines.append('## Constraints')
    lines.append('')
    lines.append('- Solo se puede tocar `{}`.'.format(rel_target))
    lines.append('- El oraculo `{}` esta congelado por `tests_sha256`: modificarlo '
                 'rompe el sello.'.format(rel_tests))
    for item in spec.get('forbids', []):
        lines.append('- Prohibido: `{}`.'.format(item))
    lines.append('')
    lines.append('{}:'.format(STOP_MARKER))
    lines.append('')
    for item in spec['stop_if']:
        lines.append('- {}'.format(item))
    lines.append('')

    return '\n'.join(lines).rstrip() + '\n'


def _merge_index(existing, block, book):
    """Inserta o reemplaza el bloque de ESTE libro, sin tocar el de los demas."""
    begin, end = INDEX_BEGIN.format(book), INDEX_END.format(book)
    if begin in existing and end in existing:
        head = existing.split(begin)[0]
        tail = existing.split(end, 1)[1]
        return head + block + tail
    return (existing.rstrip() or '# Indice de conocimiento') + '\n\n' + block + '\n'


def emit(specs, exercises_root, out_dir, book):
    """Escribe los contratos, el arbol de conocimiento y la copia de los
    instrumentos que van a correr.
    """
    knowledge = os.path.join(out_dir, 'knowledge')
    contracts_dir = os.path.join(knowledge, 'contracts')
    instruments_out = os.path.join(out_dir, 'instruments')
    instruments_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instruments')

    for spec in specs:
        _check(spec, knowledge, book)

    os.makedirs(contracts_dir, exist_ok=True)
    os.makedirs(instruments_out, exist_ok=True)
    for name in sorted(os.listdir(instruments_src)):
        if name.endswith('.py'):
            shutil.copyfile(os.path.join(instruments_src, name),
                            os.path.join(instruments_out, name))

    written = []
    for spec in specs:
        exercise_rel = 'ejercicios/{}/{}'.format(book, spec['id'])
        dst = os.path.join(out_dir, exercise_rel.replace('/', os.sep))
        # Copia del arbol completo: los contratos de nivel repo traen un
        # proyecto con subdirectorios, no un par de archivos sueltos.
        if os.path.isdir(dst):
            shutil.rmtree(dst)
        shutil.copytree(spec['_dir'], dst,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))

        rel_target = '{}/{}'.format(exercise_rel, spec.get('target', 'target.py'))
        rel_tests = '{}/{}'.format(exercise_rel, spec.get('oracle', 'oracle_test.py'))
        seal = _seal(os.path.join(out_dir, rel_tests.replace('/', os.sep)))

        path = os.path.join(contracts_dir, spec['id'] + '.md')
        with open(path, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(_render(spec, book, rel_target, rel_tests, seal, exercise_rel))
        written.append(os.path.relpath(path, out_dir).replace(os.sep, '/'))

    block = [INDEX_BEGIN.format(book), '', '## Contratos de {}'.format(book), '']
    for spec in sorted(specs, key=lambda s: s['id']):
        block.append('- [{}](contracts/{}.md) - {}'.format(
            spec['id'], spec['id'], spec['description']))
    block += ['', INDEX_END.format(book)]

    index_path = os.path.join(knowledge, 'index.md')
    existing = ''
    if os.path.isfile(index_path):
        with open(index_path, 'r', encoding='utf-8') as fh:
            existing = fh.read()
    with open(index_path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(_merge_index(existing, '\n'.join(block), book))
    written.append('knowledge/index.md')
    return written


def load_specs(exercises_root, book):
    """Lee los `spec.json` de los ejercicios de una fuente, en orden."""
    root = os.path.join(exercises_root, book)
    if not os.path.isdir(root):
        raise EmitError('no existe el directorio de ejercicios: {}'.format(root))
    specs = []
    for name in sorted(os.listdir(root)):
        spec_path = os.path.join(root, name, 'spec.json')
        if not os.path.isfile(spec_path):
            continue
        with open(spec_path, 'r', encoding='utf-8') as fh:
            spec = _con_defaults(json.load(fh), book)
        spec['_dir'] = os.path.join(root, name)
        specs.append(spec)
    if not specs:
        raise EmitError('ningun spec.json bajo {}'.format(root))
    return specs


def main(argv=None):
    """Emite los contratos de una fuente y devuelve el exit code."""
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('exercises', help='raiz de ejercicios (ej: exercises)')
    parser.add_argument('--out', default='out', help='raiz del repo generado')
    parser.add_argument('--book', required=True)
    args = parser.parse_args(argv)

    try:
        specs = load_specs(args.exercises, args.book)
        written = emit(specs, args.exercises, args.out, args.book)
    except EmitError as exc:
        print('ERROR: {}'.format(exc))
        return 1
    except (OSError, ValueError) as exc:
        print('NO-VERIFICABLE: {}'.format(exc))
        return 2

    print('OK: {} contrato(s) emitido(s)'.format(len(specs)))
    for path in written:
        print('  {}'.format(path))
    return 0


if __name__ == '__main__':
    sys.exit(main())
