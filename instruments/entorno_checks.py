#!/usr/bin/env python3
"""Instrumentos que miden el contrato entre la app y su entorno de ejecucion.

Familia nueva, y la decide el artefacto y no la fuente. Las ocho reglas salen de
The Twelve-Factor App, pero lo que las junta es **que miden**: como se declara
lo que la app necesita (dependencias, config, servicios), como se expone
(puerto), como se comporta como proceso (daemonizar, SIGTERM, logs) y si sus
despliegues coinciden. No es "el AST de un archivo" como `checks`, ni "el
proyecto corriendo" como `repo_checks`, que ejecuta comandos y mide resultados.
Aca no se ejecuta nada: se lee **la forma del proyecto**.

    dependencias  todo import de terceros esta en el manifiesto
    config        cero constantes de configuracion y credenciales en el codigo
    servicios     cero locators de servicio escritos en el codigo
    puerto        la app abre su propio puerto
    paridad       los despliegues declarados usan la misma version de cada servicio
    daemonizar    cero daemonizaciones y cero archivos PID
    sigterm       el proceso instala un manejador de SIGTERM
    logs          cero handlers de logging que escriban a archivo

**Lo que estas reglas no pueden ver, dicho de entrada.** Las que buscan un
marcador lexico —una credencial, un locator— encuentran lo que se escribe con
las palabras de la convencion. Una clave asignada a una variable llamada `x` no
la ve nadie, y eso no es un defecto que se arregle afinando la expresion
regular: es el limite de leer el codigo en vez de ejecutarlo. El umbral cero es
sobre lo que la regla alcanza a mirar, y ese alcance esta escrito abajo, en
cada `check_`, para que el verde no se lea como mas de lo que es.

Exit codes (convencion KDD):
  0  la propiedad se cumple
  1  no se cumple
  2  no se pudo verificar (falta la declaracion, o no hay que medir)

Uso:
    python entorno_checks.py --rule logs <punto_de_entrada.py>
    python entorno_checks.py --rule dependencias --manifiesto requirements.txt <e.py>
    python entorno_checks.py --rule paridad --despliegue dev=a.yml --despliegue prod=b.yml <e.py>
    python entorno_checks.py --list
"""

import argparse
import ast
import os
import re
import sys


class NoVerificable(Exception):
    """Falta el dato sin el cual la regla no se puede evaluar (exit 2)."""


# Nombres que la convencion reserva para secretos y configuracion. Es una lista
# declarada, no una heuristica abierta: se puede leer, discutir y ampliar con
# --nombre. Lo que no cubre esta dicho en el docstring del modulo.
NOMBRES_DE_CONFIG = ('password', 'passwd', 'secret', 'token', 'api_key', 'apikey',
                     'access_key', 'private_key', 'credential', 'dsn',
                     'database_url', 'conn_str', 'connection_string')

# Un locator de servicio se reconoce por su forma, no por su nombre.
LOCATOR = re.compile(
    r'^(?:postgres(?:ql)?|mysql|mariadb|mongodb|redis|amqp|kafka|memcached|'
    r'smtp|ftp|https?)://', re.I)

# Formas de daemonizar en Python. `os.fork` esta porque el fork seguido de
# setsid ES la daemonizacion clasica, y buscar solo la palabra "daemon" dejaria
# pasar justo la version escrita a mano.
DAEMONIZAR = ('daemonize', 'daemon_start', 'setsid', 'fork')

# Llamadas que escriben un archivo. Hace falta acotar a estas: la primera
# version marcaba cualquier llamada con un argumento terminado en `.pid`, y con
# eso `ruta.endswith('.pid')` —o sea PREGUNTAR si algo es un archivo PID— salia
# en rojo. Lo encontro el propio instrumento corrido sobre este repositorio,
# donde el unico hallazgo fue la linea de codigo que hace la comprobacion.
ESCRIBE = ('open', 'write_text', 'write_bytes', 'mknod')

# Handlers de logging que escriben a un archivo.
HANDLERS_A_ARCHIVO = ('FileHandler', 'RotatingFileHandler', 'TimedRotatingFileHandler',
                      'WatchedFileHandler', 'BaseRotatingHandler')

# Llamadas que abren un puerto propio.
ABRE_PUERTO = ('bind', 'listen', 'serve_forever', 'run_simple', 'create_server')

# `image: postgres:14` — la unica forma de declaracion de servicio que esta
# regla lee, y esta dicho en check_paridad por que no lee mas.
IMAGEN = re.compile(r'^\s*image:\s*["\']?([^\s:"\']+):([^\s"\']+)', re.M)


def _stdlib():
    return getattr(sys, 'stdlib_module_names', frozenset())


def _fuentes(proyecto):
    """(ruta, arbol, texto) de cada .py del proyecto que no sea prueba.

    Se excluyen las pruebas a proposito y en todas las reglas: un locator o una
    credencial de mentira en un fixture es exactamente lo que un fixture tiene
    que tener, y marcarlo pondria el instrumento en rojo por hacer bien las
    cosas.
    """
    out = []
    for raiz, dirs, archivos in os.walk(proyecto):
        dirs[:] = [d for d in dirs if d not in ('__pycache__', '.git', 'tests')]
        for nombre in sorted(archivos):
            if not nombre.endswith('.py') or nombre.startswith('test_'):
                continue
            ruta = os.path.join(raiz, nombre)
            try:
                with open(ruta, 'r', encoding='utf-8') as fh:
                    texto = fh.read()
                out.append((ruta, ast.parse(texto), texto))
            except (OSError, SyntaxError, UnicodeDecodeError) as exc:
                raise NoVerificable('no se pudo leer {}: {}'.format(ruta, exc))
    if not out:
        raise NoVerificable('el proyecto no tiene fuentes .py que medir')
    return out


def _nombre_llamado(nodo):
    """El nombre invocado en un Call, sin el receptor: `s.bind(...)` -> `bind`."""
    func = nodo.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return ''


def _literales_asignados(arbol):
    """(linea, nombre, valor) de cada asignacion de un string literal a un nombre."""
    out = []
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, (ast.Assign, ast.AnnAssign)):
            continue
        valor = nodo.value
        if not isinstance(valor, ast.Constant) or not isinstance(valor.value, str):
            continue
        objetivos = nodo.targets if isinstance(nodo, ast.Assign) else [nodo.target]
        for objetivo in objetivos:
            if isinstance(objetivo, ast.Name):
                out.append((nodo.lineno, objetivo.id, valor.value))
            elif isinstance(objetivo, ast.Attribute):
                out.append((nodo.lineno, objetivo.attr, valor.value))
    return out


def _todos_los_strings(arbol):
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str):
            yield nodo.lineno, nodo.value


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_dependencias(fuentes, opts):
    """Todo import de terceros esta declarado en el manifiesto.

    El factor pide dos cosas —declarar y aislar— y esta regla mide la primera,
    que es la que deja rastro en el artefacto. El aislamiento (un virtualenv, un
    contenedor) pasa en el entorno y no en el repositorio.

    Sin `--manifiesto` no se mide: cual archivo es el manifiesto depende del
    lenguaje y del gestor —`requirements.txt`, `pyproject.toml`, `Gemfile`— y
    elegirlo por el instrumento seria inventar la convencion del proyecto. Si el
    archivo declarado NO existe, en cambio, no hay nada que dudar: la app no
    declara sus dependencias, y eso es rojo, no exit 2.
    """
    if not opts.manifiesto:
        raise NoVerificable(
            'hay que declarar el manifiesto con --manifiesto: cual archivo es '
            'depende del gestor de paquetes del proyecto')
    ruta = opts.manifiesto if os.path.isabs(opts.manifiesto) else \
        os.path.join(opts.proyecto, opts.manifiesto)
    if not os.path.isfile(ruta):
        return [(opts.manifiesto, 0, 'el manifiesto declarado no existe: la app no '
                                     'declara ninguna dependencia')]

    with open(ruta, 'r', encoding='utf-8') as fh:
        declarado = set()
        for linea in fh:
            linea = linea.split('#')[0].strip()
            if linea:
                declarado.add(re.split(r'[<>=!\[;\s]', linea)[0].lower().replace('-', '_'))

    locales = {os.path.splitext(os.path.basename(r))[0] for r, _a, _t in fuentes}
    locales |= {d for d in os.listdir(opts.proyecto)
                if os.path.isdir(os.path.join(opts.proyecto, d))}

    out = []
    for archivo, arbol, _texto in fuentes:
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Import):
                nombres = [a.name.split('.')[0] for a in nodo.names]
            elif isinstance(nodo, ast.ImportFrom):
                if nodo.level:      # import relativo: siempre local
                    continue
                nombres = [(nodo.module or '').split('.')[0]]
            else:
                continue
            for nombre in nombres:
                if not nombre or nombre in _stdlib() or nombre in locales:
                    continue
                if nombre.lower().replace('-', '_') in declarado:
                    continue
                out.append((archivo, nodo.lineno,
                            'importa {!r} y no esta en {}: es una dependencia '
                            'implicita del sistema'.format(nombre, opts.manifiesto)))
    return out


def check_config(fuentes, opts):
    """Cero constantes de configuracion y credenciales en el codigo.

    El autor da el umbral con un test que no admite interpretacion: *si el
    repositorio no se pudiera abrir hoy sin filtrar credenciales, esta en rojo*.

    Alcance: asignaciones de un string literal a un nombre de la lista
    declarada. Un secreto asignado a `x` no lo ve, y un string vacio tampoco
    —`TOKEN = ''` es justamente el placeholder de quien ya saco la clave—.
    """
    nombres = tuple(NOMBRES_DE_CONFIG) + tuple(n.lower() for n in opts.nombre)
    out = []
    for archivo, arbol, _texto in fuentes:
        for linea, nombre, valor in _literales_asignados(arbol):
            plano = nombre.lower()
            if not valor.strip():
                continue
            if any(marca in plano for marca in nombres):
                out.append((archivo, linea,
                            '{} = "..." es configuracion escrita en el codigo: '
                            'tiene que venir del entorno'.format(nombre)))
    return out


def check_servicios(fuentes, opts):
    """Cero locators de servicio escritos en el codigo.

    "Cambiar un MySQL local por uno de un tercero sin ningun cambio en el codigo
    de la app" es medible por su contrapositivo: si el locator esta en el
    codigo, ese cambio pide tocar codigo.

    Se reconoce por la forma del valor —un esquema de URL— y no por el nombre de
    la variable, que es lo que la separa de `config`: ahi se busca como se llama,
    aca que es.
    """
    out = []
    for archivo, arbol, _texto in fuentes:
        for linea, valor in _todos_los_strings(arbol):
            if LOCATOR.match(valor.strip()):
                out.append((archivo, linea,
                            'locator de servicio en el codigo: {!r}. El recurso '
                            'adjunto se direcciona desde la config'
                            .format(valor.strip()[:60])))
    return out


def check_puerto(fuentes, opts):
    """La app abre su propio puerto.

    El factor dice que la app es autocontenida y no depende de que le inyecten
    un servidor. La mitad medible es la afirmativa: en algun lado del proyecto
    hay una llamada que ata un puerto. La otra mitad —que NO haya un servidor
    externo— es probar una ausencia sobre un artefacto que no esta en el repo.

    Es la unica regla del modulo cuyo hallazgo es la ausencia, asi que reporta
    una sola linea a nivel proyecto y no una por archivo.
    """
    for _archivo, arbol, _texto in fuentes:
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Call) and _nombre_llamado(nodo) in ABRE_PUERTO:
                return []
    return [(opts.proyecto, 0,
             'ningun archivo ata un puerto ({}): la app depende de que le '
             'inyecten un servidor'.format(', '.join(ABRE_PUERTO)))]


def check_paridad(fuentes, opts):
    """Los despliegues declarados usan el mismo tipo y version de cada servicio.

    Hacen falta dos despliegues declarados: la paridad es una relacion, y con
    uno solo no hay con que comparar. Salir verde ahi seria decir "coinciden"
    sobre un conjunto de uno.

    Lee una sola forma de declaracion, `image: nombre:version`, y esta dicho
    porque es una eleccion y no una ley: el formato del archivo de despliegue
    cambia con la herramienta, igual que el marcador de escapado cambia con el
    motor de plantillas. Un archivo declarado sin ninguna imagen sale con exit 2
    y no verde.
    """
    if len(opts.despliegue) < 2:
        raise NoVerificable(
            'hay que declarar al menos dos despliegues con --despliegue '
            'nombre=ruta: la paridad es una relacion y con uno solo no hay con '
            'que comparar')

    declarados = {}
    for entrada in opts.despliegue:
        if '=' not in entrada:
            raise NoVerificable('formato esperado --despliegue nombre=ruta, no {!r}'
                                .format(entrada))
        nombre, ruta = entrada.split('=', 1)
        completa = ruta if os.path.isabs(ruta) else os.path.join(opts.proyecto, ruta)
        if not os.path.isfile(completa):
            raise NoVerificable('el despliegue {!r} apunta a {} y no existe'
                                .format(nombre, ruta))
        with open(completa, 'r', encoding='utf-8') as fh:
            servicios = dict(IMAGEN.findall(fh.read()))
        if not servicios:
            raise NoVerificable(
                'el despliegue {!r} no declara ninguna imagen: esta regla lee '
                '"image: nombre:version" y no encontro ninguna'.format(nombre))
        declarados[nombre] = servicios

    base_nombre, base = sorted(declarados.items())[0]
    out = []
    for nombre, servicios in sorted(declarados.items())[1:]:
        for servicio in sorted(set(base) | set(servicios)):
            aca, alla = servicios.get(servicio), base.get(servicio)
            if aca is None:
                out.append((nombre, 0, '{} corre {} y {} no lo tiene'
                            .format(base_nombre, servicio, nombre)))
            elif alla is None:
                out.append((nombre, 0, '{} corre {} y {} no lo tiene'
                            .format(nombre, servicio, base_nombre)))
            elif aca != alla:
                out.append((nombre, 0, '{}: {} usa {} y {} usa {}'
                            .format(servicio, base_nombre, alla, nombre, aca)))
    return out


def check_daemonizar(fuentes, opts):
    """Cero daemonizaciones y cero archivos PID.

    Prohibicion plana del autor —"never daemonize or write PID files"— y por eso
    el umbral es cero sin discusion. `fork` y `setsid` estan en la lista porque
    el fork seguido de setsid ES la daemonizacion escrita a mano, y buscar solo
    la palabra "daemon" dejaria pasar justo esa.

    El archivo PID se marca solo cuando alguien lo ESCRIBE. Preguntar si una
    ruta termina en `.pid` no es escribir un archivo PID, y confundir las dos
    cosas fue el primer hallazgo del instrumento sobre este mismo repositorio.
    """
    out = []
    for archivo, arbol, _texto in fuentes:
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Call):
                llamado = _nombre_llamado(nodo)
                if llamado in DAEMONIZAR:
                    out.append((archivo, nodo.lineno,
                                '{}(): el proceso se administra desde afuera, no se '
                                'daemoniza solo'.format(llamado)))
                if llamado not in ESCRIBE:
                    continue
                for arg in nodo.args:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str) \
                            and arg.value.endswith('.pid'):
                        out.append((archivo, nodo.lineno,
                                    'escribe un archivo PID ({!r}): de los procesos '
                                    'se ocupa el gestor del sistema'.format(arg.value)))
    return out


def check_sigterm(fuentes, opts):
    """El proceso instala un manejador de SIGTERM.

    El apagado ordenado que pide el factor —dejar de escuchar, terminar lo que
    esta en curso, salir— empieza por enterarse, y de eso queda rastro en el
    codigo: `signal.signal(signal.SIGTERM, ...)`. Que el manejador ademas haga
    lo correcto no lo mide esta regla, y decirlo importa: verde aca significa
    "se entera", no "apaga bien".
    """
    for _archivo, arbol, _texto in fuentes:
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, ast.Call) or _nombre_llamado(nodo) != 'signal':
                continue
            for arg in nodo.args:
                if isinstance(arg, ast.Attribute) and arg.attr == 'SIGTERM':
                    return []
                if isinstance(arg, ast.Name) and arg.id == 'SIGTERM':
                    return []
    return [(opts.proyecto, 0,
             'nadie instala un manejador de SIGTERM: el proceso no se entera de '
             'que lo estan apagando')]


def check_logs(fuentes, opts):
    """Cero handlers de logging que escriban a archivo.

    "Nunca se ocupa del ruteo ni del almacenamiento de su flujo de salida" es
    una prohibicion, y las prohibiciones se miden por su contrapositivo: si hay
    un handler a archivo o un `basicConfig(filename=...)`, la app se esta
    ocupando del almacenamiento.
    """
    out = []
    for archivo, arbol, _texto in fuentes:
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, ast.Call):
                continue
            llamado = _nombre_llamado(nodo)
            if llamado in HANDLERS_A_ARCHIVO:
                out.append((archivo, nodo.lineno,
                            '{}: la app no rutea ni almacena su salida, escribe a '
                            'stdout'.format(llamado)))
            elif llamado == 'basicConfig':
                for kw in nodo.keywords:
                    if kw.arg == 'filename':
                        out.append((archivo, nodo.lineno,
                                    'basicConfig(filename=...): eso es escribir un '
                                    'logfile'))
    return out


RULES = {
    'config': (check_config, 'Config: cero configuracion y credenciales en el codigo'),
    'daemonizar': (check_daemonizar, 'Concurrencia: cero daemonizaciones y archivos PID'),
    'dependencias': (check_dependencias, 'Dependencias: todo import esta en el manifiesto'),
    'logs': (check_logs, 'Logs: cero handlers que escriban a archivo'),
    'paridad': (check_paridad, 'Paridad: los despliegues usan la misma version de cada servicio'),
    'puerto': (check_puerto, 'Port binding: la app abre su propio puerto'),
    'servicios': (check_servicios, 'Servicios: cero locators escritos en el codigo'),
    'sigterm': (check_sigterm, 'Desechabilidad: el proceso instala un manejador de SIGTERM'),
}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--rule')
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--proyecto', help='raiz del proyecto (por defecto, la del target)')
    parser.add_argument('--manifiesto', help='archivo de declaracion de dependencias')
    parser.add_argument('--despliegue', action='append', default=[],
                        help='nombre=ruta de un despliegue, repetible')
    parser.add_argument('--nombre', action='append', default=[],
                        help='nombre extra que cuenta como configuracion')
    parser.add_argument('target', nargs='?')
    args = parser.parse_args(argv)

    if args.list:
        for nombre in sorted(RULES):
            print('{:13} {}'.format(nombre, RULES[nombre][1]))
        return 0

    if args.rule not in RULES:
        print('NO-VERIFICABLE: regla desconocida: {!r} (ver --list)'.format(args.rule))
        return 2
    if not args.target and not args.proyecto:
        print('NO-VERIFICABLE: falta el punto de entrada del proyecto')
        return 2

    if args.proyecto:
        args.proyecto = os.path.abspath(args.proyecto)
    else:
        args.proyecto = os.path.dirname(os.path.abspath(args.target))
    if not os.path.isdir(args.proyecto):
        print('NO-VERIFICABLE: no existe el proyecto {}'.format(args.proyecto))
        return 2

    func, etiqueta = RULES[args.rule]
    try:
        violaciones = func(_fuentes(args.proyecto), args)
    except NoVerificable as exc:
        print('NO-VERIFICABLE: {}: {}'.format(etiqueta, exc))
        return 2

    if violaciones:
        print('INSTRUMENTO ROJO: {}'.format(etiqueta))
        for ruta, linea, detalle in violaciones:
            print('  {}:{}: {}'.format(os.path.basename(ruta), linea, detalle))
        return 1

    print('OK: {}'.format(etiqueta))
    return 0


if __name__ == '__main__':
    sys.exit(main())
