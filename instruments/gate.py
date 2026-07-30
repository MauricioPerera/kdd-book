#!/usr/bin/env python3
"""Runner del `test_command` de un contrato derivado de libro.

`validate_test_commands.py` ejecuta el `test_command` con ``shlex.split`` y
``subprocess.run`` SIN shell, asi que no se pueden encadenar dos comandos con
``&&``. Este runner es la respuesta a esa restriccion, y resulta ser el diseno
correcto: separa las dos cosas que un contrato derivado de un libro tiene que
verificar por separado.

  1. **Oraculo** (tests congelados): no rompiste el comportamiento.
  2. **Instrumento**: aplicaste la tecnica.

Una refactorizacion, por definicion, no cambia el comportamiento observable.
Por eso ningun test puede verificarla: el oraculo pasa igual antes y despues.
Lo que discrimina es la medicion. Y al reves, un instrumento en verde sobre
codigo roto no vale nada. Hacen falta los dos, y hace falta saber cual fallo.

Exit codes (convencion KDD):
  0  oraculo verde e instrumento verde
  1  alguno en rojo (el mensaje dice cual)
  2  no se pudo verificar

Uso:
    python instruments/gate.py <dir_ejercicio>
"""

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def _run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print('NO-VERIFICABLE: uso: gate.py <dir_ejercicio>')
        return 2

    exercise = os.path.abspath(argv[0])
    spec_path = os.path.join(exercise, 'spec.json')
    try:
        with open(spec_path, 'r', encoding='utf-8') as fh:
            spec = json.load(fh)
    except (OSError, ValueError) as exc:
        print('NO-VERIFICABLE: no se pudo leer {}: {}'.format(spec_path, exc))
        return 2

    oracle = spec.get('oracle', 'oracle_test.py')
    oracle_abs = os.path.join(exercise, oracle.replace('/', os.sep))
    if not os.path.isfile(oracle_abs):
        print('NO-VERIFICABLE: oraculo ausente: {}'.format(oracle))
        return 2

    # 1. Oraculo: el comportamiento sigue siendo el mismo. El oraculo puede
    # vivir en un subdirectorio (los contratos de nivel repo traen un proyecto
    # entero), asi que unittest corre desde su carpeta y por nombre de modulo.
    oracle_dir = os.path.dirname(oracle_abs)
    oracle_mod = os.path.splitext(os.path.basename(oracle_abs))[0]
    result = _run([sys.executable, '-m', 'unittest', '-v', oracle_mod], cwd=oracle_dir)
    if result.returncode != 0:
        print('ORACULO ROJO: cambiaste el comportamiento observable.')
        print(result.stdout)
        print(result.stderr)
        return 1

    # 2. Instrumento: la tecnica quedo aplicada.
    instrument = spec.get('instrument')
    if not instrument:
        print('NO-VERIFICABLE: el spec no declara instrumento. Una tarea sin '
              'instrumento no es un contrato: es una intencion.')
        return 2

    script = os.path.join(HERE, instrument['script'])
    if not os.path.isfile(script):
        print('NO-VERIFICABLE: instrumento inexistente: {}'.format(script))
        return 2

    target = os.path.join(exercise, spec.get('target', 'target.py').replace('/', os.sep))
    cmd = [sys.executable, script] + list(instrument.get('args', [])) + [target]
    result = _run(cmd, cwd=exercise)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    if result.returncode == 2:
        return 2
    if result.returncode != 0:
        print('El oraculo esta verde: no rompiste nada, pero no aplicaste la tecnica.')
        return 1

    print('OK: oraculo verde e instrumento verde.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
