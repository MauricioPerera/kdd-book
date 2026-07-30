#!/usr/bin/env python3
"""Memoria portable: exporta el conocimiento extraido y lo hace consultable.

El grafo OKF es para leer; esto es para que otro agente lo use sin tener los
libros. Un solo archivo con las tecnicas catalogadas, sus instrumentos y sus
enlaces, mas la forma de correr esos instrumentos sobre codigo cualquiera.

Lo que hace portable a esta memoria no es el formato sino dos propiedades que
costaron trabajo:

  - **los ids son estables entre idiomas** (`g36`, no
    `g36-evitar-desplazamientos-transitivos`), asi que dos memorias de fuentes
    distintas se pueden fusionar en vez de duplicarse;
  - **el contrato con el instrumento es el exit code**, no el mensaje, asi que
    un agente en cualquier idioma consume 0/1/2 sin traducir nada.

Subcomandos:

    exportar          arma memoria.json a partir de books/ y exercises/
    buscar <texto>    tecnicas cuyo titulo, tag o instrumento mencionan el texto
    medibles          las tecnicas con instrumento, con el comando para correrlo
    aplicar <archivo> corre sobre ese archivo todo instrumento de archivo unico
                      y dice que tecnica senala cada rojo
    fusionar a.json b.json [-o c.json]
                      une dos memorias por id de tecnica y reporta los
                      conflictos de triaje sin resolverlos

`aplicar` es la prueba de que la memoria sirve: responde "de todo lo que se,
que aplica a este codigo" sin haber leido ningun libro.

Solo stdlib.

Uso:
    python memoria.py exportar
    python memoria.py aplicar mi_modulo.py
"""

import argparse
import glob
import json
import os
import subprocess
import sys
import unicodedata

AQUI = os.path.dirname(os.path.abspath(__file__))
INSTRUMENTOS = os.path.join(AQUI, 'instruments')
POR_DEFECTO = os.path.join(AQUI, 'memoria.json')

# Familias cuyo instrumento mide UN archivo suelto: son las que `aplicar` puede
# correr sobre codigo ajeno. Las demas necesitan un proyecto, un repositorio git
# o una suite, o sea contexto que un archivo no trae.
DE_ARCHIVO_UNICO = ('checks.py', 'chain_depth.py', 'params_max.py')


# ---------------------------------------------------------------------------
# Exportar
# ---------------------------------------------------------------------------

def _contratos_por_nodo():
    """{(libro, nodo): id_del_contrato} leyendo los ejercicios."""
    out = {}
    for ruta in sorted(glob.glob(os.path.join(AQUI, 'exercises', '*', '*', 'spec.json'))):
        libro = os.path.basename(os.path.dirname(os.path.dirname(ruta)))
        with open(ruta, 'r', encoding='utf-8') as fh:
            spec = json.load(fh)
        out[(libro, spec['node'])] = spec['id']
    return out


def _reglas_disponibles():
    """[{familia, script, regla, descripcion}] de cada instrumento registrado."""
    sys.path.insert(0, INSTRUMENTOS)
    out = []
    for modulo in ('checks', 'repo_checks', 'arch_checks', 'git_checks',
                   'mutation_checks'):
        try:
            mod = __import__(modulo)
        except ImportError:
            continue
        for regla, datos in sorted(mod.RULES.items()):
            out.append({'script': modulo + '.py', 'regla': regla,
                        'descripcion': datos[-1]})
    for script in ('chain_depth.py', 'params_max.py'):
        if os.path.isfile(os.path.join(INSTRUMENTOS, script)):
            out.append({'script': script, 'regla': None,
                        'descripcion': 'instrumento dedicado'})
    return out


def exportar(destino):
    contratos = _contratos_por_nodo()
    libros, tecnicas = [], []
    for ruta in sorted(glob.glob(os.path.join(AQUI, 'books', '*.json'))):
        with open(ruta, 'r', encoding='utf-8') as fh:
            spec = json.load(fh)
        fuente = spec['source']
        nodos = spec['nodes']
        instrumentadas = sum(1 for n in nodos if n.get('verification') == 'instrumented')
        libros.append({
            'slug': fuente['slug'], 'titulo': fuente['title'],
            'autor': fuente.get('author'), 'items': len(nodos),
            'contractables': sum(1 for n in nodos if n['pile'] == 'A'),
            'instrumented': instrumentadas,
            'corpus': fuente.get('corpus'),
        })
        for n in nodos:
            tecnicas.append({
                'id': '{}/{}'.format(fuente['slug'], n['id']),
                'libro': fuente['slug'],
                'titulo': n['title'],
                'pila': n['pile'],
                'verification': n.get('verification'),
                'instrumento': n.get('instrument'),
                'umbral': n.get('threshold'),
                'por_que_no': n.get('why_not'),
                'locator': n.get('locator'),
                'alias': n.get('alias', []),
                'tags': n.get('tags', []),
                'enlaces': ['{}/{}'.format(fuente['slug'], e) if '/' not in e else e
                            for e in n.get('links', [])],
                'contrato': contratos.get((fuente['slug'], n['id'])),
            })

    memoria = {
        'formato': 'kdd-book/memoria',
        'version': 1,
        'nota_de_identidad': (
            'Los ids son el identificador del autor, no un resumen del titulo, '
            'para que sean estables entre ediciones e idiomas. Dos memorias de '
            'fuentes distintas se pueden fusionar por id.'),
        'nota_de_uso': (
            'El contrato con un instrumento es su exit code: 0 conforme, 1 '
            'violacion, 2 no se pudo verificar. Los mensajes son informativos.'),
        'libros': libros,
        'instrumentos': _reglas_disponibles(),
        'tecnicas': tecnicas,
    }
    with open(destino, 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(memoria, fh, ensure_ascii=False, indent=2)
        fh.write('\n')
    return memoria


def _cargar(ruta):
    with open(ruta, 'r', encoding='utf-8') as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------------

def _plegar(texto):
    """Minusculas y sin acentos, para que la busqueda no dependa de tildes.

    Hace falta de verdad: `buscar duplicacion` no encontraba a `G5:
    Duplicación`. Es el mismo problema de idioma que obligo a que los ids sean
    estables, asomando ahora en la capa de consulta — y una memoria que solo
    responde si escribis los acentos igual que el traductor no es consultable.
    """
    norm = unicodedata.normalize('NFKD', texto.lower())
    return ''.join(c for c in norm if not unicodedata.combining(c))


def buscar(memoria, texto):
    texto = _plegar(texto)
    return [t for t in memoria['tecnicas']
            if texto in _plegar(t['titulo'])
            or texto in _plegar(' '.join(t['tags']))
            or texto in _plegar(' '.join(t.get('alias', [])))
            or texto in _plegar(t['instrumento'] or '')]


def medibles(memoria):
    return [t for t in memoria['tecnicas'] if t['verification'] == 'instrumented'
            and t.get('instrumento')]


# ---------------------------------------------------------------------------
# Fusion
# ---------------------------------------------------------------------------

# Campos donde una discrepancia entre dos memorias es una DISCREPANCIA DE
# TRIAJE, no un detalle: dos personas clasificaron la misma tecnica distinto.
# No se resuelve sola — se reporta.
EN_CONFLICTO = ('pila', 'verification', 'instrumento', 'umbral')


def _unir(a, b):
    """Union preservando orden y sin repetir, ignorando caja y acentos.

    Comparar cadenas exactas no alcanza: al fusionar con otra edicion aparecen
    `ley de Demeter` y `Ley De Demeter` como si fueran alias distintos. Se
    conserva la primera grafia y se descartan sus variantes — un alias
    duplicado por una mayuscula ensucia la busqueda sin agregar nada.
    """
    out, vistos = [], set()
    for x in list(a) + list(b):
        clave = _plegar(x) if isinstance(x, str) else x
        if clave in vistos:
            continue
        vistos.add(clave)
        out.append(x)
    return out


def fusionar(memorias):
    """Fusiona varias memorias por id de tecnica.

    Esto es lo que los ids estables habilitan. Si el id fuera un resumen del
    titulo, la misma tecnica de dos ediciones tendria dos ids distintos y la
    fusion produciria duplicados en vez de una entrada mas rica.

    Que hace con cada campo:

      - `titulo` de la primera memoria gana, y el de las demas se guarda como
        alias: un titulo en otro idioma es exactamente un nombre alternativo.
      - `alias`, `enlaces`, `tags` se unen.
      - `instrumento` y `contrato` se completan si a una le falta y a otra no.
      - una discrepancia en pila, verification, instrumento o umbral **no se
        resuelve**: se reporta. Son juicios de triaje distintos, y elegir uno
        en silencio seria inventar un consenso que no existe.

    Devuelve (memoria_fusionada, conflictos).
    """
    fusion, orden, conflictos = {}, [], []
    for memoria in memorias:
        for t in memoria['tecnicas']:
            clave = t['id']
            if clave not in fusion:
                fusion[clave] = dict(t)
                orden.append(clave)
                continue
            previo = fusion[clave]
            for campo in EN_CONFLICTO:
                si, no = previo.get(campo), t.get(campo)
                if si and no and si != no:
                    conflictos.append({'id': clave, 'campo': campo,
                                       'valores': [si, no]})
                elif no and not si:
                    previo[campo] = no
            if t.get('titulo') and t['titulo'] != previo['titulo']:
                previo['alias'] = _unir(previo.get('alias', []), [t['titulo']])
            for campo in ('alias', 'enlaces', 'tags'):
                previo[campo] = _unir(previo.get(campo, []), t.get(campo, []))
            for campo in ('contrato', 'por_que_no', 'locator'):
                if t.get(campo) and not previo.get(campo):
                    previo[campo] = t[campo]

    libros, vistos = [], set()
    for memoria in memorias:
        for libro in memoria.get('libros', []):
            if libro['slug'] not in vistos:
                vistos.add(libro['slug'])
                libros.append(libro)

    instrumentos, claves = [], set()
    for memoria in memorias:
        for i in memoria.get('instrumentos', []):
            clave = (i['script'], i.get('regla'))
            if clave not in claves:
                claves.add(clave)
                instrumentos.append(i)

    return {
        'formato': 'kdd-book/memoria',
        'version': 1,
        'fusionada_de': len(memorias),
        'nota_de_identidad': memorias[0].get('nota_de_identidad'),
        'nota_de_uso': memorias[0].get('nota_de_uso'),
        'libros': libros,
        'instrumentos': instrumentos,
        'tecnicas': [fusion[k] for k in orden],
    }, conflictos


def aplicar(memoria, archivo):
    """Corre sobre `archivo` todo instrumento de archivo unico y reporta.

    Devuelve [(instrumento, exit_code, detalle, [tecnicas que lo citan])].
    """
    por_instrumento = {}
    for t in medibles(memoria):
        script = t['instrumento'].split()[0]
        if script in DE_ARCHIVO_UNICO:
            por_instrumento.setdefault(t['instrumento'], []).append(t['id'])

    out = []
    for instrumento, ids in sorted(por_instrumento.items()):
        partes = instrumento.split()
        cmd = [sys.executable, os.path.join(INSTRUMENTOS, partes[0])] + partes[1:] + [archivo]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        detalle = [l.strip() for l in proc.stdout.splitlines()[1:] if l.strip()]
        out.append((instrumento, proc.returncode, detalle, sorted(ids)))
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('accion', choices=('exportar', 'buscar', 'medibles',
                                          'aplicar', 'fusionar'))
    parser.add_argument('argumento', nargs='*')
    parser.add_argument('-m', '--memoria', default=POR_DEFECTO)
    parser.add_argument('-o', '--salida', default='memoria-fusionada.json')
    args = parser.parse_args(argv)

    if args.accion == 'fusionar':
        if len(args.argumento) < 2:
            print('NO-VERIFICABLE: fusionar necesita al menos dos memorias')
            return 2
        faltan = [r for r in args.argumento if not os.path.isfile(r)]
        if faltan:
            print('NO-VERIFICABLE: no existen: {}'.format(', '.join(faltan)))
            return 2
        partes = [_cargar(r) for r in args.argumento]
        resultado, conflictos = fusionar(partes)
        with open(args.salida, 'w', encoding='utf-8', newline='\n') as fh:
            json.dump(resultado, fh, ensure_ascii=False, indent=2)
            fh.write('\n')
        entradas = sum(len(p['tecnicas']) for p in partes)
        print('{} memoria(s), {} entradas -> {} tecnicas ({} fusionadas) en {}'.format(
            len(partes), entradas, len(resultado['tecnicas']),
            entradas - len(resultado['tecnicas']), args.salida))
        if conflictos:
            print('\n{} conflicto(s) de triaje, sin resolver a proposito:'.format(
                len(conflictos)))
            for c in conflictos:
                print('  {:<26} {:<14} {!r} contra {!r}'.format(
                    c['id'], c['campo'], c['valores'][0], c['valores'][1]))
            return 1
        return 0

    if args.accion == 'exportar':
        destino = (args.argumento[0] if args.argumento else args.memoria)
        memoria = exportar(destino)
        print('OK: {} tecnicas de {} libro(s), {} instrumentos -> {}'.format(
            len(memoria['tecnicas']), len(memoria['libros']),
            len(memoria['instrumentos']), destino))
        return 0

    if not os.path.isfile(args.memoria):
        print('NO-VERIFICABLE: no existe {}. Corre primero: python memoria.py '
              'exportar'.format(args.memoria))
        return 2
    memoria = _cargar(args.memoria)

    if args.accion == 'buscar':
        if not args.argumento:
            print('NO-VERIFICABLE: buscar necesita un texto')
            return 2
        consulta = ' '.join(args.argumento)
        encontradas = buscar(memoria, consulta)
        print('{} tecnica(s) para {!r}:'.format(len(encontradas), consulta))
        for t in encontradas:
            marca = {'A': 'medible', 'B': 'no medible', 'C': 'conocimiento'}[t['pila']]
            print('  {:<26} {:<11} {}'.format(t['id'], marca, t['titulo'][:44]))
            if t['instrumento']:
                print('  {:<26} -> {}'.format('', t['instrumento']))
        return 0

    if args.accion == 'medibles':
        for t in medibles(memoria):
            contrato = ' [contrato: {}]'.format(t['contrato']) if t['contrato'] else ''
            print('  {:<26} {:<44} {}{}'.format(
                t['id'], t['titulo'][:44], t['instrumento'], contrato))
        return 0

    objetivo = args.argumento[0] if args.argumento else None
    if not objetivo or not os.path.isfile(objetivo):
        print('NO-VERIFICABLE: aplicar necesita un archivo existente')
        return 2
    resultados = aplicar(memoria, objetivo)
    rojos = [r for r in resultados if r[1] == 1]
    print('{}: {} instrumento(s) corridos, {} en rojo\n'.format(
        args.argumento, len(resultados), len(rojos)))
    for instrumento, codigo, detalle, ids in resultados:
        if codigo != 1:
            continue
        print('  {}'.format(instrumento))
        for linea in detalle[:3]:
            print('      {}'.format(linea))
        print('      senala: {}'.format(', '.join(ids)))
    return 1 if rojos else 0


if __name__ == '__main__':
    sys.exit(main())
