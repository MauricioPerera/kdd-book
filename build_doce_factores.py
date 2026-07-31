#!/usr/bin/env python3
"""Construye books/doce-factores.json a partir de los titulos de 12factor.net.

Quinta fuente, y el quinto genero: un **manifiesto**. Las cuatro anteriores
fueron un libro de codigo, uno de arquitectura, uno de proceso y documentacion
de referencia. Este documento no explica ni describe: **prescribe, y nada mas**.

Se eligio por una prediccion falsable, hecha ANTES de triajar y escrita aca
para que se pueda contrastar: si la contractabilidad la decide que el autor
haya operacionalizado la tecnica —el hallazgo de las cuatro fuentes previas—
entonces un documento sin una sola linea de relleno tiene que quedar **por
encima de los libros de codigo** (48,5% y 45,5%). Si hubiera dado 20%, la
hipotesis estaba mal. Dio 62,5%.

**Advertencia de corpus: es el mas chico de las cinco.** 16 titulos. Pero no es
una muestra: cada factor es una pagina con titulo y bajada y sin subsecciones
—comprobado pagina por pagina— asi que 16 es el documento entero. Lo que si
cambia es la granularidad: con n=16, cada item vale 6,3 puntos, y un solo
juicio de triaje distinto mueve el porcentaje mas que en Codigo Limpio. El
numero es real; la precision implicita, no.

Lo que esta fuente pone a prueba y las otras no: **la mitad de sus tecnicas
medibles no leen codigo**. Leen el manifiesto de dependencias, el historial de
releases, los archivos de despliegue, el punto de entrada. Es la primera vez
que el artefacto de la mayoria de las tecnicas es la **forma del proyecto** y
no su codigo fuente.

Entrada: el volcado de titulos, una linea por entrada:

    <indice>| H<nivel> | <ruta> | <titulo>

Uso:
    python build_doce_factores.py [books/doce-factores-toc.txt] [-o books/doce-factores.json]
"""

import argparse
import json
import os
import re
import sys

CL = 'codigo-limpio'
AJ = 'arquitectura-java'
SX = 'scrum-xp'

# (primer_indice, ultimo_indice, nombre)
SECCIONES = [
    (1, 4, 'preambulo'),
    (5, 16, 'los doce factores'),
]

# Pila A: (instrumento, umbral).
#
# Diez de doce. Ninguna es `proxy`: todas leen el proyecto —codigo, manifiesto,
# historial, archivos de despliegue— y ninguna depende de un registro que llene
# una persona. Es lo esperable en un manifiesto de operaciones: describe cosas
# que el sistema hace o no hace, no cosas que un equipo declara haber hecho.
#
# Ocho viven en `entorno_checks`, familia nueva que esta fuente obligo a
# inventar, y dos en `git_checks`, que ya existia: `codebase` y `releaseid`
# miden el historial, que es donde vive lo que esos dos factores prescriben.
A_NODES = {
    5: ('git_checks.py --rule codebase',
        'un codebase bajo control de versiones por aplicacion'),
    6: ('entorno_checks.py --rule dependencias',
        'cero dependencias implicitas del sistema'),
    7: ('entorno_checks.py --rule config',
        'cero: el repositorio se podria abrir hoy sin filtrar credenciales'),
    8: ('entorno_checks.py --rule servicios',
        'cero locators en el codigo'),
    9: ('git_checks.py --rule releaseid',
        'cero releases sin identificador propio'),
    11: ('entorno_checks.py --rule puerto',
         'la app exporta su servicio sin servidor inyectado'),
    12: ('entorno_checks.py --rule daemonizar',
         'cero'),
    13: ('entorno_checks.py --rule sigterm',
         'un manejador de SIGTERM por proceso de larga vida'),
    14: ('entorno_checks.py --rule paridad',
         'cero diferencias de tipo o version entre despliegues'),
    15: ('entorno_checks.py --rule logs',
         'cero: el proceso escribe a stdout'),
}

# Pila B: tecnica real cuya propiedad definitoria no es medible.
B_NODES = {10, 16}

WHY_NOT = {
    10: ('la ausencia de estado compartido no se decide leyendo el proyecto. Lo '
         'que si seria medible —escrituras a disco— tiene usos que el propio '
         'texto autoriza ("a brief, single-transaction cache"), asi que el '
         'umbral no puede ser cero y no hay otro que el autor haya fijado'),
    16: ('"el codigo de administracion viaja con el de la aplicacion" es '
         'medible solo si alguien declara cuales de los archivos son de '
         'administracion, y esa clasificacion es el juicio, no la medicion. Lo '
         'demas que pide el factor —correr contra el mismo release— pasa en la '
         'ejecucion, no en el artefacto'),
}

ALIAS = {
    5: ['un codebase por aplicacion', 'one codebase', 'codebase'],
    6: ['declaracion explicita de dependencias', 'explicit dependencies',
        'dependency manifest'],
    7: ['configuracion en el entorno', 'config in the environment',
        'variables de entorno', 'env vars'],
    8: ['servicios de respaldo como recursos adjuntos', 'backing services',
        'attached resources'],
    9: ['separar build, release y run', 'build release run', 'release id'],
    10: ['procesos sin estado', 'stateless processes', 'share-nothing'],
    11: ['port binding', 'exportar por puerto', 'self-contained server'],
    12: ['escalar por el modelo de procesos', 'concurrency', 'process model',
         'no daemonizar'],
    13: ['desechabilidad', 'disposability', 'graceful shutdown', 'SIGTERM'],
    14: ['paridad dev/prod', 'dev prod parity'],
    15: ['logs como flujo de eventos', 'logs to stdout', 'event streams'],
    16: ['procesos de administracion', 'admin processes', 'one-off processes'],
}

# Enlaces cruzados. Pocos y hacia donde de verdad hay vecindad: esta fuente
# habla de la forma del proyecto y las otras cuatro, sobre todo, de codigo.
LINKS = {
    5: ['{}/122'.format(SX)],
    7: ['{}/g35'.format(CL), 8],
    8: ['{}/19'.format(AJ)],
    15: ['{}/07'.format(AJ)],
    9: [5],
    14: [8],
}

NOTA_CRUZADA = {
    5: ('Vecino de "Unificacion del codigo en Repositorios" de Scrum y XP, y '
        'conviene no confundirlos: Bahit mide **ramas sin integrar** y este '
        'factor mide **cuantos codebases hay por aplicacion**. Son dos '
        'propiedades distintas del mismo repositorio, y por eso comparten '
        'vecindad pero no instrumento.'),
    7: ('Es G35 de Codigo Limpio —"mantener los datos configurables en los '
        'niveles superiores"— llevado hasta el final y, sobre todo, **medible**. '
        'Martin lo deja en pila B porque que dato conviene subir es un juicio; '
        'aca el autor fija el nivel superior (el entorno) y da el umbral con un '
        'test que no admite interpretacion: si el repositorio no se puede abrir '
        'hoy sin filtrar credenciales, esta en rojo. Es el mismo par que G19 y '
        '142, o que G30 y SRP: la misma idea, y la contractabilidad la decide '
        'cual de los dos autores la operacionalizo.'),
    8: ('El "cambiar MySQL local por RDS sin tocar el codigo" es inversion de '
        'control aplicada a los recursos, o sea el principio 19 de Arquitectura '
        'Java visto desde operaciones. Caules lo mide sobre instanciacion en el '
        'codigo; aca se mide sobre donde vive el locator.'),
    15: ('Caules dedica una seccion a Log4J, que es la herramienta; este factor '
         'prescribe el destino, que es lo medible. La distincion se repite en '
         'todo el grafo: la tecnologia cae en pila C y la prescripcion sobre '
         'ella puede caer en A.'),
}

_LINEA = re.compile(r'^\s*(\d+)\|\s*H(\d)\s*\|\s*(\S+)\s*\|\s*(.+?)\s*$')


def leer(texto):
    out = {}
    for linea in texto.splitlines():
        if linea.lstrip().startswith('#'):
            continue
        m = _LINEA.match(linea)
        if m:
            out[int(m.group(1))] = (int(m.group(2)), m.group(3), m.group(4))
    return out


def seccion_de(indice):
    for desde, hasta, nombre in SECCIONES:
        if desde <= indice <= hasta:
            return nombre
    return 'sin seccion'


def id_de(indice):
    """`f01`..`f12` para los factores, `s01`..`s04` para el preambulo.

    El identificador del autor es el numeral romano, o sea el ordinal, y eso no
    cambia con la traduccion. Un id derivado del titulo si cambiaria: "III.
    Config" es "III. Configuracion" en la version castellana y serian dos nodos
    distintos para la misma tecnica.
    """
    if indice <= 4:
        return 's{:02d}'.format(indice)
    return 'f{:02d}'.format(indice - 4)


def build(texto):
    entradas = leer(texto)
    faltan = [i for i in list(A_NODES) + sorted(B_NODES) if i not in entradas]
    if faltan:
        raise SystemExit('ERROR: indices del triaje que no existen: {}'.format(faltan))

    ids = {i: id_de(i) for i in entradas}

    def destino(t):
        return t if isinstance(t, str) else ids.get(t)

    nodes = []
    for indice in sorted(entradas):
        nivel, ruta, titulo = entradas[indice]
        seccion = seccion_de(indice)
        if indice in A_NODES:
            pila, verification = 'A', 'instrumented'
            instrumento, umbral = A_NODES[indice]
        elif indice in B_NODES:
            pila, verification, instrumento, umbral = 'B', 'none', None, None
        else:
            pila, verification, instrumento, umbral = 'C', 'none', None, None

        tags = ['doce-factores', seccion.replace(' ', '-'),
                {'A': 'contractable', 'B': 'no-especificable',
                 'C': 'conocimiento'}[pila]]
        if pila == 'A':
            tags.append('instrumented')

        node = {
            'id': ids[indice],
            'title': titulo,
            'description': '{} (seccion: {}).'.format(titulo, seccion),
            'type': 'Concept',
            'tags': tags,
            'pile': pila,
            'verification': verification,
            'locator': '12factor.net{}'.format(ruta),
            'alias': ALIAS.get(indice, []),
            'links': [d for d in (destino(t) for t in LINKS.get(indice, [])) if d],
        }
        if instrumento:
            node['instrument'] = instrumento
        if umbral:
            node['threshold'] = umbral
        if indice in WHY_NOT:
            node['why_not'] = WHY_NOT[indice]
        if indice in NOTA_CRUZADA:
            node['body'] = NOTA_CRUZADA[indice]
        nodes.append(node)

    return {
        'source': {
            'slug': 'doce-factores',
            'title': 'The Twelve-Factor App',
            'author': 'Adam Wiggins y colaboradores',
            'file': '12factor.net (sitio, 13 paginas)',
            'pages': 13,
            'extracted_with': 'titulos del sitio, verificados pagina por pagina',
            'tags': ['fuente', 'manifiesto', 'doce-factores'],
            'corpus': ('Los 16 titulos del documento: cuatro de preambulo y los doce '
                       'factores. CORPUS MAS CHICO DE LAS CINCO FUENTES, pero no es '
                       'una muestra: cada factor es una pagina con titulo y bajada y '
                       'sin subsecciones, comprobado pagina por pagina, asi que 16 es '
                       'el documento entero. Con n=16 cada item vale 6,3 puntos: el '
                       'porcentaje es real, la precision implicita no.'),
        },
        'nodes': nodes,
    }, entradas


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('toc', nargs='?',
                        default=os.path.join('books', 'doce-factores-toc.txt'))
    parser.add_argument('-o', '--out',
                        default=os.path.join('books', 'doce-factores.json'))
    args = parser.parse_args(argv)

    with open(args.toc, 'r', encoding='utf-8') as fh:
        spec, entradas = build(fh.read())

    os.makedirs(os.path.dirname(args.out) or '.', exist_ok=True)
    with open(args.out, 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(spec, fh, ensure_ascii=False, indent=2)
        fh.write('\n')

    total = len(spec['nodes'])
    pilas = {'A': 0, 'B': 0, 'C': 0}
    for n in spec['nodes']:
        pilas[n['pile']] += 1
    print('OK: {} nodos -> {}'.format(total, args.out))
    print('  A={} ({:.1f}%)  B={}  C={}'.format(
        pilas['A'], 100.0 * pilas['A'] / total, pilas['B'], pilas['C']))
    factores = [n for n in spec['nodes'] if n['id'].startswith('f')]
    a_factores = sum(1 for n in factores if n['pile'] == 'A')
    print('  solo los doce factores: {}/{} ({:.1f}%)'.format(
        a_factores, len(factores), 100.0 * a_factores / len(factores)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
