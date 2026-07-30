#!/usr/bin/env python3
"""Instrumento: profundidad maxima de cadena de accesos (Ley de Demeter).

Mide la heuristica G36 de Codigo Limpio, que el autor define de forma
mecanica: "si A colabora con B y B con C, no queremos que los modulos que usan
A sepan nada sobre C (por ejemplo, a.getB().getC().doSomething())".

La profundidad es la cantidad de accesos a atributo encadenados sobre una misma
base. `a.b` vale 1, `a.b().c()` vale 2. Las llamadas intermedias no cuentan como
eslabon: lo que cuenta es cuantos saltos de propiedad hace el modulo.

Excepcion deliberada: cuando la base de la cadena es `self`, se descuenta un
eslabon. La Ley de Demeter permite explicitamente que un metodo llame a metodos
de sus propios campos, asi que `self.direccion.etiqueta()` es conforme y no debe
contarse como violacion. Sin esta regla el instrumento haria imposible la propia
refactorizacion que exige: delegar hacia abajo siempre pasa por un campo propio.

Exit codes (convencion KDD):
  0  ninguna cadena supera el maximo
  1  al menos una cadena lo supera
  2  no se pudo verificar (archivo ilegible o no parseable)

Uso:
    python chain_depth.py --max 1 <archivo.py> [<archivo.py> ...]
"""

import argparse
import ast
import sys


def _chain_depth(node):
    """Cantidad de saltos de propiedad en la cadena que termina en `node`.

    Devuelve la profundidad ya descontando el eslabon gratuito de `self`.
    """
    depth = 0
    current = node
    while True:
        if isinstance(current, ast.Attribute):
            depth += 1
            current = current.value
        elif isinstance(current, ast.Call):
            current = current.func
        elif isinstance(current, ast.Subscript):
            current = current.value
        else:
            break
    # Acceder a un campo propio no es un salto: Demeter lo permite.
    if isinstance(current, ast.Name) and current.id == 'self' and depth > 0:
        depth -= 1
    return depth


def _is_chain_root(node, parents):
    """True si `node` es el extremo exterior de su cadena.

    Evita contar la misma cadena una vez por eslabon: solo se mide desde
    afuera hacia adentro. Una llamada NO corta la cadena, solo la envuelve
    (`a.b().c()` es una sola cadena de profundidad 2), asi que al encontrar
    un Call que llama a este nodo hay que seguir subiendo por encima de el.
    """
    current = node
    while True:
        parent = parents.get(id(current))
        if parent is None:
            return True
        if isinstance(parent, ast.Attribute) and parent.value is current:
            return False
        if isinstance(parent, ast.Call) and parent.func is current:
            current = parent
            continue
        return True


def measure(path):
    """Devuelve [(linea, profundidad, fuente)] de cada cadena del archivo."""
    with open(path, 'r', encoding='utf-8') as fh:
        source = fh.read()
    tree = ast.parse(source, filename=path)

    parents = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[id(child)] = parent

    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute):
            continue
        if not _is_chain_root(node, parents):
            continue
        depth = _chain_depth(node)
        if depth:
            found.append((node.lineno, depth, ast.unparse(node)))
    return sorted(found)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--max', type=int, required=True,
                        help='profundidad maxima permitida')
    parser.add_argument('files', nargs='+')
    args = parser.parse_args(argv)

    violations = []
    for path in args.files:
        try:
            for lineno, depth, src in measure(path):
                if depth > args.max:
                    violations.append((path, lineno, depth, src))
        except (OSError, SyntaxError) as exc:
            print('NO-VERIFICABLE: {}: {}'.format(path, exc))
            return 2

    if violations:
        print('INSTRUMENTO ROJO: chain_depth_max={}'.format(args.max))
        for path, lineno, depth, src in violations:
            print('  {}:{}: profundidad {} -> {}'.format(path, lineno, depth, src))
        return 1

    print('OK: ninguna cadena supera chain_depth_max={}'.format(args.max))
    return 0


if __name__ == '__main__':
    sys.exit(main())
