#!/usr/bin/env python3
"""Construye books/agile-manifesto.json a partir del triaje del Manifesto Agil.

El Manifesto por el Desarrollo de Software Agil (Kent Beck et al., 2001) es una
lista cerrada de 17 items (1 declaracion, 4 valores, 12 principios) que
`agilemanifesto.org` publica verbatim. Este script los toma del archivo
`agile-manifesto.txt` (la captura verbatim de los 17 items, extraida de
`agile-manifesto.html` y `agile-manifesto-principles.html`) y los tria a mano en
pilas A/B/C segun el metodo kdd:

  - pila A (contractable/instrumentada): el autor operacionalizo una propiedad
    de texto con un umbral que un artefacto puede leer. Ningun item lo hace
    aqui, asi que A = 0.
  - pila B (tecnica real, sin propiedad definitoria medible): el item describe
    una tecnica real pero no operacionaliza un umbral concreto, o el instrumento
    existente es un subconjunto/superconjunto (falsas positivas). Se registra
    el `why_not` por que no es contractable.
  - pila C (conocimiento): juicio estetico, filosofico o de prioridad sin
    tecnica operacionalizable.

El candidato a pila A mas directo es el Principio 3 ("Deliver working software
frequently, from a couple of weeks to a couple of months"), cuyo hermano
scrum-xp/024 operacionaliza `git_checks.py --rule cadencia` como pila A. Pero
cadencia mide solo el hueco entre tags de release en el historial de git:
(1) este checkout no tiene .git, asi que devuelve NO-VERIFICABLE (exit 2); (2)
mide un umbral SUPERIOR, no la ventana del principio (2 semanas a 2 meses) ni
la preferencia al minimo; (3) no verifica "software FUNCIONANDO" (eso es
repo_checks e2). Reusar cadencia como unico umbral seria un subconjunto parcial,
no una medicion fiel —el mismo razonamiento que deja a zp10 en pila B cuando
arch_checks.excepciones es un superconjunto. Con A = 0 no hay contratos que
emitir (gate 2 no aplica), y la cobertura per-rule de test_cobertura se mantiene
en verde sin ejercicios nuevos ni instrumentos nuevos.

Entrada:
    agile-manifesto.txt   captura verbatim de los 17 items del manifesto agil

Uso:
    python build_agile_manifesto.py [agile-manifesto.txt] [-o books/agile-manifesto.json]
"""

__all__ = ['build', 'leer', 'main']

import argparse
import json
import os
import re
import sys

# Pila A: (instrumento, umbral). 0 de 17 — ningun item operacionaliza una
# propiedad de artefacto con un umbral automatizado fiel. El candidato mas
# directo (Principio 3 ~ cadencia) se rechaza: cadencia mide hueco entre tags,
# no 'software funcionando' ni la ventana de tiempo del principio, y devuelve
# NO-VERIFICABLE en repositorios sin .git.
A_NODES = {}

# Pila B: tecnica real cuya propiedad definitoria no es medible por artefacto.
# 7 de 17. Cada why_not cita el instrumento hermano de scrum-xp que se rechaza
# y por que es un proxy inadecuado.
B_NODES = {6, 8, 12, 13, 14, 15, 17}

# Pila C: conocimiento, estetica o juicio sin tecnica operacionalizable.
# 10 de 17.
C_INDICES = {1, 2, 3, 4, 5, 7, 9, 10, 11, 16}

# Razon por la que cada B no es contractable (pila B).
WHY_NOT = {
    6: ("La entrega temprana y continua de software valioso es la tecnica que "
        "scrum-xp operacionaliza en `git_checks.py --rule cadencia` "
        "(scrum-xp/024, pila A). Pero cadencia mide el hueco entre tags de "
        "release en el historial de git, y este checkout no tiene .git, asi que "
        "devuelve NO-VERIFICABLE (exit 2). Mas alla de ello, el umbral de "
        "cadencia verifica solo la frecuencia de marcaje, no 'satisfacer al "
        "cliente' ni 'software valioso': el valor lo juzga el cliente y la "
        "continuidad exige un ritmo sostenido que un tag cada <=60 dias no "
        "garantiza. El proxy es un subconjunto parcial sobre una propiedad que "
        "exige razonamiento de equipo, no un umbral de artefacto."),
    8: ("El candidato mas directo es `git_checks.py --rule cadencia` "
        "(scrum-xp/024), el unico instrumento que lee el historial de git para "
        "este principio. Tiene tres fallas: (1) devuelve NO-VERIFICABLE en este "
        "checkout (sin .git); (2) mide solo el hueco SUPERIOR entre tags, mientras "
        "el principio propone una ventana (2 semanas a 2 meses) con preferencia "
        "al minimo —un rango y una preferencia que cadencia no captura; (3) "
        "requiere 'software FUNCIONANDO' y cadencia no verifica tests en verde "
        "(eso es repo_checks e2, distinto). Reusar cadencia como unico umbral "
        "seria un subconjunto parcial: la tecnica es real, la propiedad "
        "definitoria no es medible con un solo instrumento sobre artefacto."),
    12: ("El instrumento `repo_checks.py --rule e2` (scrum-xp/085, 108, 110) "
         "confirma 'software funcionando' corriendo la suite de tests en verde. "
         "Pero 'medida PRIMARIA de progreso' implica una priorizacion frente a "
         "otras medidas (historias completadas, funcionalidades, valor de "
         "negocio) —una decision de prioridad que ningun artefacto puede "
         "determinar. La propiedad medible es el subconjunto 'tests en verde'; "
         "el juicio de 'medida primaria' es razonamiento de equipo, no umbral de "
         "artefacto."),
    13: ("scrum-xp/079 ('semana de 40 horas') clasifica el mismo concepto como "
         "pila B: aunque su titulo menciona 40 horas, la autora Bahit no fija un "
         "numero —habla de no exigir mas esfuerzo del humanamente disponible, que "
         "es un juicio sobre carga de trabajo. En el manifesto, 'desarrollo "
         "sostenible' y 'ritmo constante indefinidamente' son aspiraciones sobre "
         "bienestar del equipo; ningun artefacto de codigo o git puede leer "
         "'sostenibilidad' ni 'ritmo'. No hay umbral artifactual fiel."),
    14: ("Existen instrumentos sobre propiedades individuales (repo_checks g24 "
         "sobre convenciones, checks metlineas/g5 sobre longitud y duplicacion), "
         "pero 'excelencia tecnica' o 'buen diseno' como conceptos holisticos no "
         "tienen un umbral: son juicios de calidad global. Cada instrumento mide "
         "una propiedad concreta que el autor de codigo puede cumplir sin que el "
         "resultado sea 'excelente' en sentido amplio. La propiedad definitoria "
         "no es automatizable fielmente."),
    15: ("Al igual que el aforismo zen 'Flat is better than nested' (zp05, pila B), "
         "'simplicidad' es un juicio de diseno: decir cuanto codigo es 'demasiado' "
         "exige un numero ajeno al texto. scrum-xp/030 clasifica la misma idea "
         "como B. No hay una propiedad de artefacto que determine 'simple' —solo "
         "proxies debiles como lineas o metodos cortos, que el autor del manifesto "
         "no operacionaliza con un umbral concreto."),
    17: ("scrum-xp/032 ('inspeccionar y adaptar') clasifica la retrospectiva como "
         "pila A con verificacion `proxy` (calendario: la retrospectiva ocurrio al "
         "cerrar el sprint) —un registro que llena una persona, no una propiedad de "
         "codigo. El manifesto exige 'reflexionar sobre como ser mas efectivo' y "
         "'ajustar el comportamiento', lo cual es razonamiento humano sobre el "
         "proceso del equipo, no algo que un artefacto pueda leer. Incluso el "
         "proxy de calendario de scrum-xp no es un instrumento sobre codigo: "
         "confirmar que una reunion ocurrio no verifica que el equipo realice el "
         "ajuste."),
}

# Nombres canonigos reconocidos (alias) por item. Las B llevan alias no vacio
# (para busqueda cruzada y enlace entre libros); las C, alias vacio.
ALIAS = {
    1: [],
    2: [],
    3: [],
    4: [],
    5: [],
    6: ['entrega temprana y continua', 'early and continuous delivery',
        'satisfacer al cliente', 'satisfy the customer'],
    7: [],
    8: ['entregas frecuentes', 'frequent delivery', 'entregas cortas',
       'short releases', 'couple of weeks'],
    9: [],
    10: [],
    11: [],
    12: ['software funcionando como medida', 'working software is the measure',
         'medida de progreso', 'primary measure of progress'],
    13: ['ritmo sostenible', 'sustainable pace', 'semana de 40 horas',
         '40 hour week', 'constant pace', 'sustainable development'],
    14: ['excelencia tecnica', 'technical excellence', 'buen diseno',
         'good design'],
    15: ['simplicidad', 'simplicity', 'maximize work not done',
         'trabajo no realizado'],
    16: [],
    17: ['retrospectiva', 'retrospective', 'inspeccionar y adaptar',
         'inspect and adapt'],
}

# Titulos cortos (etiquetas) por item — el titulo es una etiqueta que cambia
# con la edicion; el id (amNN) es estable y no depende del titulo.
TITULOS = {
    1: 'Declaracion del manifiesto agil',
    2: 'Individuos e interacciones sobre procesos y herramientas',
    3: 'Software funcionando sobre documentacion exhaustiva',
    4: 'Colaboracion con el cliente sobre negociacion de contratos',
    5: 'Responder al cambio sobre seguir un plan',
    6: 'Entrega temprana y continua de software valioso',
    7: 'Bienvenidos requisitos cambiantes',
    8: 'Entregar software funcionando frecuentemente',
    9: 'Trabajo diario entre personas y negocio',
    10: 'Individuos motivados con entorno y soporte',
    11: 'Conversacion cara a cara',
    12: 'Software funcionando como medida de progreso',
    13: 'Ritmo sostenible e indefinido',
    14: 'Excelencia tecnica y buen diseno',
    15: 'Simplicidad',
    16: 'Equipos autoorganizados emergen',
    17: 'Reflexion y ajuste del equipo',
}

SOURCE = {
    'slug': 'agile-manifesto',
    'title': 'Manifesto for Agile Software Development',
    'author': ('Kent Beck, Mike Beedle, Arie van Bennekum, Alistair Cockburn, '
               'Ward Cunningham, Martin Fowler, James Grenning, Jim Highsmith, '
               'Andrew Hunt, Ron Jeffries, Jon Kern, Brian Marick, Robert C. '
               'Martin, Steve Mellor, Ken Schwaber, Jeff Sutherland, Dave Thomas'),
    'file': 'agilemanifesto.org (agile-manifesto.html, agile-manifesto-principles.html)',
    'pages': 2,
    'extracted_with': 'triaje a mano de los 17 items del manifesto agil (1 '
                      'declaracion + 4 valores + 12 principios), tomados verbatim '
                      'de agile-manifesto.html y agile-manifesto-principles.html. '
                      'La cobertura instrumentada es 0% porque ningun item '
                      'operacionaliza una propiedad de artefacto con un umbral '
                      'automatizado fiel.',
    'tags': ['fundamento', 'agil', 'manifesto'],
    'corpus': 'Lista cerrada de 17 items del Manifesto Agil (1 declaracion, 4 '
              'valores, 12 principios), tomados verbatim de agilemanifesto.org. '
              'Cada item es un juicio sobre como trabaja un equipo, no una '
              'propiedad de artefacto que un instrumento pueda leer. La fraccion '
              'instrumentada es 0%: el candidato mas directo (cadencia de '
              'git_checks para P1/P3) mide solo el hueco entre tags de release, '
              'no "entrega continua de software valioso" ni "software '
              'funcionando", y devuelve NO-VERIFICABLE en repositorios sin .git.',
}

LOCATOR = 'agilemanifesto.org'

_PILA_TAG = {'A': 'contractable', 'B': 'no-especificable', 'C': 'conocimiento'}


def leer(texto):
    """Indexa la captura verbatim del manifesto agil por numero de item.

    Saltea la linea de titulo y las lineas en blanco; el resto, en orden, son
    los 17 items (descripcion verbatim del autor).
    """
    out = {}
    idx = 0
    for linea in texto.splitlines():
        s = linea.strip()
        if not s or s.startswith('The Agile Manifesto'):
            continue
        idx += 1
        out[idx] = s
    return out


def build(texto):
    """Arma el spec de la fuente a partir de la captura verbatim y el triaje."""
    entradas = leer(texto)
    faltan = [i for i in list(A_NODES) + sorted(B_NODES) + sorted(C_INDICES)
              if i not in entradas]
    if faltan:
        raise SystemExit(
            'ERROR: indices del triaje que no existen en la captura: {}'
            .format(faltan))

    if len(entradas) != 17:
        raise SystemExit(
            'ERROR: la captura tiene {} items, se esperaban 17'
            .format(len(entradas)))

    nodes = []
    for indice in sorted(entradas):
        if indice in A_NODES:
            pila, verification = 'A', 'instrumented'
            instrumento, umbral = A_NODES[indice]
        elif indice in B_NODES:
            pila, verification, instrumento, umbral = (
                'B', 'human_rubric', None, None)
        else:
            pila, verification, instrumento, umbral = (
                'C', 'none', None, None)

        tags = ['manifesto', 'agil', 'fundamento', _PILA_TAG[pila]]
        if pila == 'A':
            tags.append('instrumented')

        node = {
            'id': 'am{:02d}'.format(indice),
            'title': TITULOS[indice],
            'description': entradas[indice],
            'type': 'Concept',
            'tags': tags,
            'pile': pila,
            'verification': verification,
            'locator': LOCATOR,
            'alias': ALIAS.get(indice, []),
            'links': [],
        }
        if instrumento:
            node['instrument'] = instrumento
        if umbral:
            node['threshold'] = umbral
        if indice in WHY_NOT:
            node['why_not'] = WHY_NOT[indice]
        nodes.append(node)

    return {'source': SOURCE, 'nodes': nodes}, entradas


def main(argv=None):
    """Lee la captura verbatim, arma el JSON de la fuente y lo escribe."""
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('manifesto', nargs='?', default='agile-manifesto.txt',
                        help='captura verbatim de los 17 items del manifesto agil')
    parser.add_argument('-o', '--out',
                        default=os.path.join('books', 'agile-manifesto.json'))
    args = parser.parse_args(argv)

    with open(args.manifesto, 'r', encoding='utf-8') as fh:
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
    print('  (corpus finito de 17 items del manifesto agil; la cobertura '
          'instrumentada es 0%)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
