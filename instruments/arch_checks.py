#!/usr/bin/env python3
"""Instrumentos de arquitectura: propiedades del grafo de imports y de instanciacion.

Familia propia, separada de `checks.py`, porque estas mediciones necesitan que
el proyecto **declare** algo: cuales son sus capas, que capa puede llamar a
cual, cual es el esquema de la tabla. Eso no entra en el `--rule --max` de las
demas, y ademas es correcto que sea explicito: una regla de capas que el
instrumento adivine no es una regla, es una opinion.

El hallazgo que justifica esta familia es que los principios de arquitectura
resultaron tan medibles como las heuristicas de codigo limpio, y por una razon
que no es obvia: **son propiedades del grafo de dependencias e instanciacion**,
que es justo lo que el analisis estatico lee de forma nativa. "Semantico" para
un humano no implica "no medible" para un parser.

Exit codes (convencion KDD):
  0  la propiedad se cumple
  1  no se cumple
  2  no se pudo verificar (falta la declaracion que la regla necesita)

Uso:
    python arch_checks.py --rule capas \\
        --capa presentacion=vistas --capa negocio=servicios \\
        --capa persistencia=dao \\
        --permite presentacion>negocio --permite negocio>persistencia <dir>
    python arch_checks.py --list
"""

__all__ = [
    'NoVerificable',
    'check_aop',
    'check_capas',
    'check_coc',
    'check_excepciones',
    'check_instanciacion',
    'check_isp',
    'main',
]

import argparse
import ast
import json
import os
import sys

# Sobre que mide esta familia: el proyecto entero: manifiesto, punto de entrada o suite.
#
# Lo declara cada familia y no una lista en `memoria.py`, porque esa lista
# ya quedo vieja dos veces. `aplicar` elige por este campo que instrumentos
# puede correr sobre lo que le dieron; sin el, agregar una familia la deja
# afuera en silencio y nada falla.
ARTEFACTO = 'proyecto'


class NoVerificable(Exception):
    """Falta la declaracion sin la cual la regla no se puede evaluar (exit 2)."""


# ---------------------------------------------------------------------------
# Andamiaje
# ---------------------------------------------------------------------------

def _modulos(raiz):
    """[(modulo, ruta, arbol)] de cada .py del arbol, sin tests."""
    out = []
    for base, _dirs, files in os.walk(raiz):
        for nombre in sorted(files):
            if not nombre.endswith('.py') or nombre.startswith('test_'):
                continue
            ruta = os.path.join(base, nombre)
            rel = os.path.relpath(ruta, raiz).replace(os.sep, '.')[:-3]
            with open(ruta, 'r', encoding='utf-8') as fh:
                out.append((rel, ruta, ast.parse(fh.read(), filename=ruta)))
    return sorted(out)


def _imports(arbol):
    """[(modulo_importado, linea)] de cada import del arbol."""
    out = []
    for node in ast.walk(arbol):
        if isinstance(node, ast.Import):
            for alias in node.names:
                out.append((alias.name, node.lineno))
        elif isinstance(node, ast.ImportFrom) and node.module:
            out.append((node.module, node.lineno))
    return out


def _capa_de(modulo, capas):
    for nombre, prefijos in capas.items():
        for prefijo in prefijos:
            if modulo == prefijo or modulo.startswith(prefijo + '.'):
                return nombre
    return None


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_capas(raiz, opts):
    """SRP, MVC, DAO, capa de servicio: nadie importa fuera de lo permitido.

    Es el instrumento que sostiene cinco tecnicas del libro, porque las cinco
    son la misma propiedad vista desde distintas alturas: quien puede depender
    de quien.
    """
    if not opts.capa:
        raise NoVerificable('hay que declarar las capas con --capa nombre=prefijo')
    capas = {}
    for declaracion in opts.capa:
        nombre, _, prefijos = declaracion.partition('=')
        if not prefijos:
            raise NoVerificable('--capa mal formada: {!r}'.format(declaracion))
        capas[nombre] = [p.strip() for p in prefijos.split(',') if p.strip()]

    permitido = set()
    for arista in opts.permite or []:
        origen, _, destino = arista.partition('>')
        if not destino:
            raise NoVerificable('--permite mal formada: {!r}'.format(arista))
        permitido.add((origen.strip(), destino.strip()))

    out = []
    for modulo, ruta, arbol in _modulos(raiz):
        origen = _capa_de(modulo, capas)
        if origen is None:
            continue
        for importado, linea in _imports(arbol):
            destino = _capa_de(importado, capas)
            if destino is None or destino == origen:
                continue
            if (origen, destino) not in permitido:
                out.append(('{}:{}: la capa {!r} importa {!r} de la capa {!r}, '
                            'que no esta permitido'
                            .format(os.path.basename(ruta), linea, origen,
                                    importado, destino), False))
    return out


def check_instanciacion(raiz, opts):
    """IOC, Factory, DI: una clase no crea a sus colaboradores.

    La definicion es la de la autora del libro: "las dependencias que una clase
    tiene no deben ser asignadas por ella misma sino por un agente externo". Se
    marca cada instanciacion, dentro del cuerpo de una clase, de un tipo que el
    modulo importo — o sea de un colaborador y no de una estructura propia.
    """
    exentos = set(opts.permite_crear or [])
    out = []
    for modulo, ruta, arbol in _modulos(raiz):
        if modulo in exentos or os.path.basename(ruta)[:-3] in exentos:
            continue
        importados = set()
        for node in ast.walk(arbol):
            if isinstance(node, ast.ImportFrom):
                importados.update(a.asname or a.name for a in node.names)
            elif isinstance(node, ast.Import):
                importados.update((a.asname or a.name).split('.')[0] for a in node.names)
        for clase in ast.walk(arbol):
            if not isinstance(clase, ast.ClassDef):
                continue
            for node in ast.walk(clase):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                        and node.func.id in importados:
                    out.append(('{}:{}: {} crea a su colaborador {}() en vez de '
                                'recibirlo'.format(os.path.basename(ruta),
                                                   node.lineno, clase.name,
                                                   node.func.id), False))
    return out


def check_excepciones(raiz, opts):
    """Manejo de excepciones: nada de catch mudos ni demasiado amplios."""
    out = []
    for _modulo, ruta, arbol in _modulos(raiz):
        for node in ast.walk(arbol):
            if not isinstance(node, ast.ExceptHandler):
                continue
            nombre = os.path.basename(ruta)
            if node.type is None:
                out.append(('{}:{}: `except:` sin tipo atrapa hasta lo que no '
                            'sabe manejar'.format(nombre, node.lineno), False))
            elif isinstance(node.type, ast.Name) and node.type.id in ('Exception',
                                                                     'BaseException'):
                out.append(('{}:{}: `except {}` es demasiado amplio'
                            .format(nombre, node.lineno, node.type.id), False))
            cuerpo = [s for s in node.body if not isinstance(s, ast.Pass)]
            if not cuerpo:
                out.append(('{}:{}: bloque except vacio: el error se pierde en '
                            'silencio'.format(nombre, node.lineno), False))
    return out


def check_isp(raiz, opts):
    """ISP: nadie depende de metodos que nunca va a usar.

    La definicion del libro: "una clase cliente A que tiene una dependencia con
    la clase B no debe verse forzada a depender de metodos de la clase B que no
    vaya a usar jamas". Se compara, por cada clase del proyecto, cuantos de sus
    metodos publicos usa cada cliente.
    """
    metodos_por_clase = {}
    arboles = _modulos(raiz)
    for _modulo, _ruta, arbol in arboles:
        for clase in ast.walk(arbol):
            if isinstance(clase, ast.ClassDef):
                metodos_por_clase[clase.name] = {
                    m.name for m in clase.body
                    if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and not m.name.startswith('_')}

    out = []
    for _modulo, ruta, arbol in arboles:
        for cliente in ast.walk(arbol):
            if not isinstance(cliente, ast.ClassDef):
                continue
            anotados = {}
            for node in ast.walk(cliente):
                if isinstance(node, ast.arg) and isinstance(node.annotation, ast.Name):
                    if node.annotation.id in metodos_por_clase:
                        anotados[node.arg] = node.annotation.id
            for variable, tipo in sorted(anotados.items()):
                usados = set()
                for node in ast.walk(cliente):
                    if isinstance(node, ast.Attribute) \
                            and isinstance(node.value, ast.Name) and node.value.id == variable:
                        usados.add(node.attr)
                disponibles = metodos_por_clase[tipo]
                sin_usar = disponibles - usados
                if usados and len(sin_usar) > opts.max_sin_usar:
                    out.append(('{}: {} depende de {} pero no usa {} de sus {} '
                                'metodos: {}'
                                .format(os.path.basename(ruta), cliente.name, tipo,
                                        len(sin_usar), len(disponibles),
                                        ', '.join(sorted(sin_usar))), False))
    return out


_TRANSVERSAL = {'log', 'logger', 'logging', 'debug', 'info', 'warning', 'error',
                'commit', 'rollback', 'begin_transaction'}


def check_aop(raiz, opts):
    """AOP: lo transversal no vive dentro de las clases de negocio.

    Requiere declarar cuales son los modulos de negocio: sin eso, cualquier
    llamada a un logger parece una violacion, incluida la del propio logger.
    """
    if not opts.negocio:
        raise NoVerificable(
            'hay que declarar los modulos de negocio con --negocio prefijo')
    prefijos = [p.strip() for p in opts.negocio for p in p.split(',') if p.strip()]

    out = []
    for modulo, ruta, arbol in _modulos(raiz):
        if not any(modulo == p or modulo.startswith(p + '.') for p in prefijos):
            continue
        for node in ast.walk(arbol):
            atributo = None
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    atributo = node.func.attr
                elif isinstance(node.func, ast.Name):
                    atributo = node.func.id
            if atributo and atributo.lower() in _TRANSVERSAL:
                out.append(('{}:{}: codigo transversal ({}) dentro de una clase '
                            'de negocio'.format(os.path.basename(ruta),
                                                node.lineno, atributo), False))
    return out


def check_coc(raiz, opts):
    """COC: los campos de la clase coinciden con las columnas de la tabla.

    Es la convencion concreta que declara el libro. Requiere el esquema: sin el
    no hay contra que comparar, y adivinarlo seria inventar la convencion.
    """
    if not opts.esquema:
        raise NoVerificable(
            'hay que pasar el esquema de tablas con --esquema archivo.json')
    try:
        with open(opts.esquema, 'r', encoding='utf-8') as fh:
            esquema = json.load(fh)
    except (OSError, ValueError) as exc:
        raise NoVerificable('no se pudo leer el esquema: {}'.format(exc))

    out = []
    for _modulo, ruta, arbol in _modulos(raiz):
        for clase in ast.walk(arbol):
            if not isinstance(clase, ast.ClassDef) or clase.name not in esquema:
                continue
            campos = set()
            for node in ast.walk(clase):
                if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) \
                        and node.value.id == 'self' and isinstance(node.ctx, ast.Store):
                    campos.add(node.attr)
            columnas = set(esquema[clase.name])
            if campos != columnas:
                faltan = sorted(columnas - campos)
                sobran = sorted(campos - columnas)
                detalle = []
                if faltan:
                    detalle.append('faltan {}'.format(', '.join(faltan)))
                if sobran:
                    detalle.append('sobran {}'.format(', '.join(sobran)))
                out.append(('{}: {} no sigue la convencion con su tabla: {}'
                            .format(os.path.basename(ruta), clase.name,
                                    '; '.join(detalle)), False))
    return out


RULES = {
    'aop': (check_aop, 'AOP: lo transversal fuera de las clases de negocio'),
    'capas': (check_capas, 'Capas: nadie importa fuera de lo permitido'),
    'coc': (check_coc, 'COC: los campos de la clase siguen la convencion de la tabla'),
    'excepciones': (check_excepciones, 'Excepciones: sin catch mudos ni amplios'),
    'instanciacion': (check_instanciacion, 'IOC/DI/Factory: la clase no crea a sus colaboradores'),
    'isp': (check_isp, 'ISP: nadie depende de metodos que no usa'),
}


def main(argv=None):
    """Corre la regla pedida sobre los archivos dados y devuelve el exit
    code.
    """
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--rule')
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--capa', action='append')
    parser.add_argument('--permite', action='append')
    parser.add_argument('--permite-crear', action='append')
    parser.add_argument('--negocio', action='append')
    parser.add_argument('--esquema')
    parser.add_argument('--max-sin-usar', type=int, default=0)
    # El proyecto a escanear se puede fijar explicitamente. Hace falta porque
    # estas reglas miden relaciones ENTRE modulos: derivar la raiz del archivo
    # que se esta tocando escanearia solo su capa, y una regla de capas que ve
    # una sola capa siempre esta en verde.
    parser.add_argument('--proyecto')
    parser.add_argument('raiz', nargs='?', default='.')
    args = parser.parse_args(argv)

    if args.list:
        for nombre in sorted(RULES):
            print('{:14} {}'.format(nombre, RULES[nombre][1]))
        return 0

    if args.rule not in RULES:
        print('NO-VERIFICABLE: regla desconocida: {!r} (ver --list)'.format(args.rule))
        return 2
    objetivo = args.proyecto or args.raiz
    raiz = objetivo if os.path.isdir(objetivo) else os.path.dirname(objetivo)
    if not os.path.isdir(raiz):
        print('NO-VERIFICABLE: no existe el directorio: {}'.format(objetivo))
        return 2

    func, etiqueta = RULES[args.rule]
    try:
        hallazgos = func(raiz, args)
    except NoVerificable as exc:
        print('NO-VERIFICABLE: {}: {}'.format(etiqueta, exc))
        return 2
    except (OSError, SyntaxError) as exc:
        print('NO-VERIFICABLE: {}: {}'.format(etiqueta, exc))
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
