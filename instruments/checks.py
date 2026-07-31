#!/usr/bin/env python3
"""Instrumentos deterministas para las heuristicas contractables de Codigo Limpio.

Un solo modulo con un registro de checks en vez de un script por heuristica:
todos comparten el andamiaje AST, asi que agregar una medicion cuesta una
funcion corta y una entrada en RULES.

Cada check mide UNA propiedad definitoria y devuelve las violaciones con linea
y detalle. Ninguno interpreta: si la heuristica no tiene propiedad medible, no
esta aca — esta declarada en su nodo OKF como pila B.

Exit codes (convencion KDD):
  0  ninguna violacion
  1  al menos una violacion
  2  no se pudo verificar (archivo ilegible o no parseable)

Uso:
    python checks.py --rule g29 --max 0 <archivo.py> [...]
    python checks.py --list
"""

import argparse
import ast
import io
import re
import sys
import tokenize

# Sobre que mide esta familia: un archivo .py suelto: no necesita contexto.
#
# Lo declara cada familia y no una lista en `memoria.py`, porque esa lista
# ya quedo vieja dos veces. `aplicar` elige por este campo que instrumentos
# puede correr sobre lo que le dieron; sin el, agregar una familia la deja
# afuera en silencio y nada falla.
ARTEFACTO = 'archivo-python'


# ---------------------------------------------------------------------------
# Andamiaje comun
# ---------------------------------------------------------------------------

class NoVerificable(Exception):
    """El check no puede decidir con lo que ve (exit 2, no exit 1).

    Distinta de "no hay violaciones": significa que la medicion no es posible,
    no que dio bien. Confundirlas es como un instrumento que da verde cuando se
    queda sin bateria.
    """


MUTATORS = {'append', 'extend', 'insert', 'remove', 'pop', 'clear',
            'sort', 'update', 'add', 'discard', 'setdefault'}

TRIVIAL_NUMBERS = {0, 1, 2, -1, 100}


def _parents(tree):
    table = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            table[id(child)] = parent
    return table


def _functions(tree):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node


def _param_names(func):
    spec = func.args
    return [a.arg for a in spec.posonlyargs + spec.args + spec.kwonlyargs]


def _scope_lines(node):
    """Cantidad de lineas que abarca el cuerpo de una funcion."""
    end = getattr(node, 'end_lineno', None) or node.lineno
    return max(1, end - node.lineno)


def _is_self_base(node):
    current = node
    while isinstance(current, (ast.Attribute, ast.Call, ast.Subscript)):
        current = (current.value if not isinstance(current, ast.Call)
                   else current.func)
    return isinstance(current, ast.Name) and current.id == 'self'


def _names_assigned(func):
    """{nombre: linea} de los locales asignados en la funcion."""
    found = {}
    for node in ast.walk(func):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    found.setdefault(target.id, node.lineno)
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
            if isinstance(node.target, ast.Name):
                found.setdefault(node.target.id, node.lineno)
    return found


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_f2(tree, src, limit):
    """F2 argumentos de salida: un parametro que la funcion muta."""
    out = []
    for func in _functions(tree):
        params = set(_param_names(func))
        for node in ast.walk(func):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Subscript) and \
                            isinstance(target.value, ast.Name) and target.value.id in params:
                        out.append((node.lineno, 'muta el parametro {!r}'.format(target.value.id)))
                    elif isinstance(target, ast.Attribute) and \
                            isinstance(target.value, ast.Name) and target.value.id in params:
                        out.append((node.lineno, 'muta el parametro {!r}'.format(target.value.id)))
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                base = node.func.value
                if isinstance(base, ast.Name) and base.id in params and \
                        node.func.attr in MUTATORS:
                    out.append((node.lineno, 'muta el parametro {!r} con .{}()'.format(
                        base.id, node.func.attr)))
    return out


def check_f3(tree, src, limit):
    """F3/G15 argumento de indicador o selector: un booleano que elige camino."""
    out = []
    for func in _functions(tree):
        flags = set()
        spec = func.args
        defaults = list(spec.defaults) + [d for d in spec.kw_defaults if d is not None]
        positional = spec.posonlyargs + spec.args
        for arg, default in zip(positional[len(positional) - len(spec.defaults):],
                                spec.defaults):
            if isinstance(default, ast.Constant) and isinstance(default.value, bool):
                flags.add(arg.arg)
        for arg in positional + spec.kwonlyargs:
            annotation = getattr(arg, 'annotation', None)
            if isinstance(annotation, ast.Name) and annotation.id == 'bool':
                flags.add(arg.arg)
        del defaults
        params = set(_param_names(func))
        for node in ast.walk(func):
            test = getattr(node, 'test', None)
            if test is None:
                continue
            for sub in ast.walk(test):
                if isinstance(sub, ast.Name) and sub.id in params:
                    if sub.id in flags or isinstance(test, ast.Name):
                        out.append((node.lineno,
                                    'el parametro {!r} decide el camino'.format(sub.id)))
    return out


def check_g29(tree, src, limit):
    """G29 condicionales negativas."""
    out = []
    for node in ast.walk(tree):
        test = getattr(node, 'test', None)
        if test is None or not isinstance(node, (ast.If, ast.While, ast.IfExp)):
            continue
        for sub in ast.walk(test):
            if isinstance(sub, ast.UnaryOp) and isinstance(sub.op, ast.Not):
                out.append((node.lineno, 'condicion negada con `not`'))
            elif isinstance(sub, ast.Compare):
                for op in sub.ops:
                    if isinstance(op, (ast.NotEq, ast.NotIn, ast.IsNot)):
                        out.append((node.lineno, 'condicion negada ({})'.format(
                            type(op).__name__)))
    return out


def check_g23(tree, src, limit):
    """G23 polimorfismo antes que if/else: cadena que discrimina sobre lo mismo."""
    out = []
    seen = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.If) or id(node) in seen:
            continue
        chain, current = [], node
        while isinstance(current, ast.If):
            seen.add(id(current))
            chain.append(current)
            current = current.orelse[0] if (len(current.orelse) == 1 and
                                            isinstance(current.orelse[0], ast.If)) else None
        if len(chain) <= limit:
            continue
        discriminants = set()
        for branch in chain:
            if isinstance(branch.test, ast.Compare) and len(branch.test.ops) == 1:
                discriminants.add(ast.dump(branch.test.left))
        if len(discriminants) == 1:
            out.append((node.lineno,
                        'cadena de {} ramas discriminando sobre la misma expresion'.format(
                            len(chain))))
    return out


def check_g28(tree, src, limit):
    """G28 encapsular condicionales: operadores booleanos en un mismo test."""
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.If, ast.While, ast.IfExp)):
            continue
        count = 0
        for sub in ast.walk(node.test):
            if isinstance(sub, ast.BoolOp):
                count += len(sub.values) - 1
        if count > limit:
            out.append((node.lineno,
                        'condicion con {} operadores booleanos'.format(count)))
    return out


def check_g14(tree, src, limit):
    """G14 envidia de caracteristicas: mas accesos ajenos que propios."""
    out = []
    for func in _functions(tree):
        if not _param_names(func) or _param_names(func)[0] != 'self':
            continue
        own = foreign = 0
        by_object = {}
        for node in ast.walk(func):
            if not isinstance(node, ast.Attribute):
                continue
            if _is_self_base(node):
                own += 1
            else:
                foreign += 1
                base = node.value
                while isinstance(base, (ast.Attribute, ast.Call)):
                    base = base.value if not isinstance(base, ast.Call) else base.func
                if isinstance(base, ast.Name):
                    by_object[base.id] = by_object.get(base.id, 0) + 1
        if foreign > own and foreign > limit:
            worst = max(by_object, key=by_object.get) if by_object else '?'
            out.append((func.lineno,
                        '{}() usa {} accesos ajenos contra {} propios (sobre todo a {!r})'
                        .format(func.name, foreign, own, worst)))
    return out


def check_g10(tree, src, limit):
    """G10 separacion vertical: distancia entre declarar y usar."""
    out = []
    for func in _functions(tree):
        assigned = _names_assigned(func)
        first_use = {}
        for node in ast.walk(func):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                if node.id in assigned and node.id not in first_use:
                    first_use[node.id] = node.lineno
        for name, decl in sorted(assigned.items()):
            use = first_use.get(name)
            if use is None:
                continue
            distance = use - decl
            if distance > limit:
                out.append((decl, '{!r} se declara y se usa {} lineas despues'.format(
                    name, distance)))
    return out


def check_g25(tree, src, limit):
    """G25 numeros magicos: literales numericos sin nombre en el cuerpo."""
    out = []
    constants = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    constants.add(id(node.value))
    for func in _functions(tree):
        for node in ast.walk(func):
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) \
                    and not isinstance(node.value, bool):
                if node.value in TRIVIAL_NUMBERS or id(node) in constants:
                    continue
                out.append((node.lineno, 'numero magico {!r}'.format(node.value)))
    return out


def check_n5(tree, src, limit):
    """N5 nombres extensos para ambitos extensos.

    El autor ancla la regla: "los nombres i y j son correctos si su ambito tiene
    cinco lineas de longitud". Se generaliza ese ancla: un nombre de L
    caracteres se admite en un ambito de hasta L*5 lineas.
    """
    out = []
    for func in _functions(tree):
        lines = _scope_lines(func)
        for name, lineno in sorted(_names_assigned(func).items()):
            if name.startswith('_'):
                continue
            allowed = len(name) * 5
            if lines > allowed:
                out.append((lineno,
                            '{!r} ({} chars) en un ambito de {} lineas; admite hasta {}'
                            .format(name, len(name), lines, allowed)))
    return out


def check_n6(tree, src, limit):
    """N6 evitar codificaciones: prefijos de tipo o de miembro en identificadores."""
    pattern = re.compile(r'^(m_|s_|g_|sz|lpsz|str[A-Z_]|int[A-Z_]|b[A-Z]|i[A-Z]|f[A-Z])')
    out = []
    for func in _functions(tree):
        candidates = dict(_names_assigned(func))
        for name in _param_names(func):
            candidates.setdefault(name, func.lineno)
        for name, lineno in sorted(candidates.items()):
            if pattern.match(name):
                out.append((lineno, 'identificador codificado: {!r}'.format(name)))
    return out


def check_g8(tree, src, limit):
    """G8 exceso de informacion: superficie publica de una clase."""
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        public = [n.name for n in node.body
                  if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                  and not n.name.startswith('_')]
        if len(public) > limit:
            out.append((node.lineno, '{} expone {} metodos publicos'.format(
                node.name, len(public))))
    return out


def check_g7(tree, src, limit):
    """G7 clases base que dependen de sus variantes."""
    subclasses = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                if isinstance(base, ast.Name):
                    subclasses.setdefault(base.id, set()).add(node.name)
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or node.name not in subclasses:
            continue
        variants = subclasses[node.name]
        for sub in ast.walk(node):
            if isinstance(sub, ast.Name) and sub.id in variants:
                out.append((sub.lineno, '{} nombra a su variante {}'.format(
                    node.name, sub.id)))
    return out


def check_g9(tree, src, limit):
    """G9/F4 codigo muerto: funciones que ni se exportan ni se referencian.

    Requiere `__all__`. Sin el no se puede saber que funciones son la API del
    modulo y cuales sobran: una funcion publica no la llama nadie *dentro* de
    su propio archivo, y marcarla como muerta seria un falso positivo sobre
    todos los modulos bien escritos. Cuando falta, el check no adivina: avisa
    que no puede verificar.
    """
    exportados = None
    for node in tree.body:
        targets = node.targets if isinstance(node, ast.Assign) else (
            [node.target] if isinstance(node, ast.AnnAssign) else [])
        for target in targets:
            if isinstance(target, ast.Name) and target.id == '__all__':
                value = node.value
                if isinstance(value, (ast.List, ast.Tuple)):
                    exportados = {e.value for e in value.elts
                                  if isinstance(e, ast.Constant)}
    if exportados is None:
        raise NoVerificable(
            'el modulo no declara `__all__`: sin saber cual es su API publica no '
            'se puede distinguir una funcion muerta de una exportada')

    defined = {n.name: n.lineno for n in tree.body
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    used = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            used.add(node.id)
        elif isinstance(node, ast.Attribute):
            used.add(node.attr)
    return [(lineno, 'funcion ni exportada ni referenciada: {}()'.format(name))
            for name, lineno in sorted(defined.items())
            if name not in exportados and name not in used]


def check_g12(tree, src, limit):
    """G12 desorden: imports sin usar y locales asignados que nadie lee."""
    out = []
    imported = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported[(alias.asname or alias.name).split('.')[0]] = node.lineno
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imported[alias.asname or alias.name] = node.lineno
    loaded = {n.id for n in ast.walk(tree)
              if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    loaded |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    for name, lineno in sorted(imported.items()):
        if name not in loaded:
            out.append((lineno, 'import sin usar: {}'.format(name)))
    for func in _functions(tree):
        used = {n.id for n in ast.walk(func)
                if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
        for name, lineno in sorted(_names_assigned(func).items()):
            if name not in used and not name.startswith('_'):
                out.append((lineno, 'variable asignada y nunca leida: {!r}'.format(name)))
    return out


def check_g33(tree, src, limit):
    """G33 encapsular condiciones de limite: subexpresion repetida."""
    counts, lines = {}, {}
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub)):
            key = ast.dump(node)
            counts[key] = counts.get(key, 0) + 1
            lines.setdefault(key, node.lineno)
    out = []
    for key, count in sorted(counts.items(), key=lambda kv: lines[kv[0]]):
        if count > limit + 1:
            out.append((lines[key],
                        'expresion de limite repetida {} veces sin nombre'.format(count)))
    return out


def check_g5(tree, src, limit):
    """G5 duplicacion: secuencias de sentencias identicas repetidas."""
    blocks = {}
    for node in ast.walk(tree):
        body = getattr(node, 'body', None)
        if not isinstance(body, list) or len(body) < 2:
            continue
        for i in range(len(body) - 1):
            key = ast.dump(ast.Module(body=body[i:i + 2], type_ignores=[]))
            blocks.setdefault(key, []).append(body[i].lineno)
    out = []
    for key, occurrences in sorted(blocks.items(), key=lambda kv: kv[1][0]):
        if len(occurrences) > limit + 1:
            out.append((occurrences[0],
                        'bloque de 2 sentencias repetido en lineas {}'.format(
                            ', '.join(str(n) for n in occurrences))))
    return out


def check_c5(tree, src, limit):
    """C5 codigo comentado: un comentario que parsea como codigo."""
    out = []
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(src).readline))
    except (tokenize.TokenError, IndentationError):
        return out
    for token in tokens:
        if token.type != tokenize.COMMENT:
            continue
        text = token.string.lstrip('#').strip()
        if len(text) < 6 or text.startswith(('type:', 'noqa', 'pylint')):
            continue
        try:
            parsed = ast.parse(text)
        except (SyntaxError, ValueError):
            continue
        if parsed.body and not isinstance(parsed.body[0], ast.Expr):
            out.append((token.start[0], 'comentario que es codigo: {!r}'.format(text[:60])))
        elif parsed.body and isinstance(parsed.body[0], ast.Expr) and \
                isinstance(parsed.body[0].value, ast.Call):
            out.append((token.start[0], 'comentario que es codigo: {!r}'.format(text[:60])))
    return out


def _operadores(expr):
    """Operadores de una expresion, contando el arbol entero."""
    total = 0
    for node in ast.walk(expr):
        if isinstance(node, ast.BoolOp):
            total += len(node.values) - 1
        elif isinstance(node, ast.Compare):
            total += len(node.ops)
        elif isinstance(node, (ast.BinOp, ast.UnaryOp)):
            total += 1
        elif isinstance(node, ast.IfExp):
            total += 1
    return total


def check_exprops(tree, src, limit):
    """Expresiones extensas (Bahit): operadores acumulados en una expresion.

    Es la misma refactorizacion que G19 de Codigo Limpio, que alli quedo en
    pila B. Aca es medible porque la autora no reclama nada de los nombres: su
    ejemplo extrae a `$a`, `$b`, `$c`, `$d`, asi que lo unico que queda de la
    tecnica es bajar la complejidad de la expresion, que es contable.
    """
    out = []
    for node in ast.walk(tree):
        expr = None
        if isinstance(node, ast.Return) and node.value is not None:
            expr = node.value
        elif isinstance(node, ast.Assign):
            expr = node.value
        elif isinstance(node, (ast.If, ast.While)):
            expr = node.test
        if expr is None:
            continue
        cantidad = _operadores(expr)
        if cantidad > limit:
            out.append((node.lineno,
                        'expresion con {} operadores'.format(cantidad)))
    return out


def check_metlineas(tree, src, limit):
    """Metodos extensos (Bahit): lineas del cuerpo de una funcion."""
    out = []
    for func in _functions(tree):
        lineas = _scope_lines(func)
        if lineas > limit:
            out.append((func.lineno, '{}() ocupa {} lineas'.format(func.name, lineas)))
    return out


def check_anatomia(tree, src, limit):
    """Anatomia del test (Bahit): un test sin asercion no prueba nada.

    Una prueba que corre y no afirma nada sale 0 igual, y esa es justo la forma
    silenciosa de no tener pruebas. El limite no aplica: se exige al menos una
    asercion por metodo `test_*`.
    """
    del limit
    out = []
    for func in _functions(tree):
        if not func.name.startswith('test'):
            continue
        aserciones = 0
        for node in ast.walk(func):
            if isinstance(node, ast.Assert):
                aserciones += 1
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                    and node.func.attr.startswith('assert'):
                aserciones += 1
            elif isinstance(node, ast.With):
                for item in node.items:
                    if isinstance(item.context_expr, ast.Call) and \
                            isinstance(item.context_expr.func, ast.Attribute) and \
                            item.context_expr.func.attr.startswith('assertRaises'):
                        aserciones += 1
        if aserciones == 0:
            out.append((func.lineno,
                        '{}() no contiene ninguna asercion'.format(func.name)))
    return out


def check_j2(tree, src, limit):
    """J2 no heredar constantes: heredar de una clase que solo aporta valores.

    La heuristica es de Java (implementar una interfaz para quedarse con sus
    constantes) pero la maniobra existe igual en Python: heredar de una clase
    que no tiene comportamiento, solo constantes, para escribirlas sin
    calificar. Eso usa la herencia como atajo de sintaxis y ata la jerarquia a
    algo que no es un tipo.
    """
    solo_constantes = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        tiene_metodos = any(isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))
                            for m in node.body)
        constantes = [m for m in node.body
                      if isinstance(m, (ast.Assign, ast.AnnAssign))]
        if constantes and not tiene_metodos:
            solo_constantes.add(node.name)

    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id in solo_constantes:
                out.append((node.lineno,
                            '{} hereda de {}, que solo aporta constantes'
                            .format(node.name, base.id)))
    return out


_SUPPRESSIONS = re.compile(
    r'#\s*(noqa|type:\s*ignore|pylint:\s*disable|mypy:\s*ignore)'
    r'|@SuppressWarnings|@unittest\.skip|@pytest\.mark\.skip')


def check_g4(tree, src, limit):
    """G4 medidas de seguridad canceladas: supresiones de linter o tests apagados."""
    out = []
    for number, line in enumerate(src.splitlines(), start=1):
        match = _SUPPRESSIONS.search(line)
        if match:
            out.append((number, 'medida de seguridad cancelada: {!r}'.format(
                match.group(0).strip())))
    return out


# ---------------------------------------------------------------------------
# Registro
# ---------------------------------------------------------------------------

RULES = {
    'anatomia': (check_anatomia, 0, 'Anatomia del test: sin asercion no prueba nada'),
    'c5': (check_c5, 0, 'C5 codigo comentado'),
    'exprops': (check_exprops, 3, 'Expresiones extensas: operadores por expresion'),
    'j2': (check_j2, 0, 'J2 no heredar constantes'),
    'metlineas': (check_metlineas, 15, 'Metodos extensos: lineas por funcion'),
    'f2': (check_f2, 0, 'F2 argumentos de salida'),
    'f3': (check_f3, 0, 'F3/G15 argumento de indicador o selector'),
    'g4': (check_g4, 0, 'G4 medidas de seguridad canceladas'),
    'g5': (check_g5, 0, 'G5 duplicacion'),
    'g7': (check_g7, 0, 'G7 clase base que depende de su variante'),
    'g8': (check_g8, 7, 'G8 exceso de informacion (superficie publica)'),
    'g9': (check_g9, 0, 'G9/F4 codigo muerto'),
    'g10': (check_g10, 5, 'G10 separacion vertical'),
    'g12': (check_g12, 0, 'G12 desorden'),
    'g14': (check_g14, 2, 'G14 envidia de caracteristicas'),
    'g23': (check_g23, 2, 'G23 polimorfismo antes que if/else'),
    'g25': (check_g25, 0, 'G25 numeros magicos'),
    'g28': (check_g28, 1, 'G28 encapsular condicionales'),
    'g29': (check_g29, 0, 'G29 evitar condicionales negativas'),
    'g33': (check_g33, 0, 'G33 encapsular condiciones de limite'),
    'n5': (check_n5, 0, 'N5 nombres extensos para ambitos extensos'),
    'n6': (check_n6, 0, 'N6 evitar codificaciones'),
}

# Heuristicas que comparten instrumento porque el libro las define igual.
ALIASES = {'g15': 'f3', 'f4': 'g9'}


def run(rule, paths, limit):
    func, default, _label = RULES[rule]
    if limit is None:
        limit = default
    violations = []
    for path in paths:
        with open(path, 'r', encoding='utf-8') as fh:
            src = fh.read()
        tree = ast.parse(src, filename=path)
        for lineno, detail in func(tree, src, limit):
            violations.append((path, lineno, detail))
    return sorted(violations), limit


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--rule')
    parser.add_argument('--max', type=int, default=None)
    parser.add_argument('--list', action='store_true')
    parser.add_argument('files', nargs='*')
    args = parser.parse_args(argv)

    if args.list:
        for name in sorted(RULES):
            print('{:5} max={:<3} {}'.format(name, RULES[name][1], RULES[name][2]))
        for alias, target in sorted(ALIASES.items()):
            print('{:5} -> {}'.format(alias, target))
        return 0

    rule = ALIASES.get(args.rule, args.rule)
    if rule not in RULES:
        print('NO-VERIFICABLE: regla desconocida: {!r} (ver --list)'.format(args.rule))
        return 2
    if not args.files:
        print('NO-VERIFICABLE: no se indicaron archivos')
        return 2

    try:
        violations, limit = run(rule, args.files, args.max)
    except NoVerificable as exc:
        print('NO-VERIFICABLE: {}: {}'.format(RULES[rule][2], exc))
        return 2
    except (OSError, SyntaxError) as exc:
        print('NO-VERIFICABLE: {}'.format(exc))
        return 2

    if violations:
        print('INSTRUMENTO ROJO: {} (max={})'.format(RULES[rule][2], limit))
        for path, lineno, detail in violations:
            print('  {}:{}: {}'.format(path, lineno, detail))
        return 1

    print('OK: {} (max={})'.format(RULES[rule][2], limit))
    return 0


if __name__ == '__main__':
    sys.exit(main())
