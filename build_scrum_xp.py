#!/usr/bin/env python3
"""Construye books/scrum-xp.json a partir de los marcadores del PDF.

Segundo libro del grafo: "Scrum y eXtreme Programming para Programadores"
(Eugenia Bahit). Los titulos salen de los 161 marcadores que la autora dejo en
el propio documento; la clasificacion es el triaje y va declarada aqui para que
sea auditable linea por linea. No se reproduce el texto de la autora.

Este libro es la prueba de la regla de ruteo por seccion. Su fraccion
`instrumented` global es 14,4%, pero eso no es un valor intermedio: es el
promedio ponderado de dos poblaciones. Los capitulos sobre codigo dan 29-55% y
los capitulos sobre proceso dan 0-3%. Ninguna seccion cae en el medio.

Entrada: el volcado de marcadores, una linea por entrada:

    <indice>| L<nivel> | <titulo> | p<pagina>

Uso:
    python build_scrum_xp.py <sxp_toc.txt> [-o books/scrum-xp.json]
"""

import argparse
import json
import os
import re
import sys
import unicodedata

CL = 'codigo-limpio'  # slug del primer libro, para los enlaces cruzados

# Contenedores de nivel 1: sus hijos llevan el contenido, contarlos duplicaria.
CONTENEDORES = {1, 33, 70, 101, 117, 135, 147, 155}

# Secciones, para poder medir la fraccion instrumented de cada una por separado
# — que es lo que decide el ruteo. (primer_indice, ultimo_indice, nombre)
SECCIONES = [
    (2, 32, 'introduccion y agilismo'),
    (34, 69, 'scrum'),
    (71, 100, 'programacion extrema y coding dojo'),
    (102, 116, 'tdd'),
    (118, 134, 'integracion continua'),
    (136, 146, 'refactoring'),
    (148, 154, 'combinar scrum y xp'),
    (156, 161, 'kanban'),
]

# Pila A: (instrumento, umbral, verification). `instrumented` significa que el
# instrumento lee el artefacto del que trata la tecnica (codigo, build, git);
# `proxy` que lee un registro que llena una persona (el tablero).
A_NODES = {
    24: ('git_checks.py --rule cadencia', 'hueco entre entregas <= 60 dias', 'instrumented'),
    32: ('tablero: retrospectiva registrada por sprint', 'una por sprint', 'proxy'),

    47: ('tablero: el backlog existe y esta ordenado', 'orden total definido', 'proxy'),
    48: ('tablero: campos obligatorios del item', 'sin campos vacios', 'proxy'),
    49: ('tablero: prioridad asignada a cada item', 'sin items sin prioridad', 'proxy'),
    50: ('tablero: estimacion presente en cada item', 'sin items sin estimar', 'proxy'),
    52: ('tablero: criterios de aceptacion no vacios', 'sin historias sin criterios', 'proxy'),
    53: ('tablero: el sprint backlog sale del tope del backlog', 'subconjunto del tope', 'proxy'),
    54: ('tablero: cada historia tiene tareas', 'sin historias sin descomponer', 'proxy'),
    55: ('build del incremento', 'exit 0', 'proxy'),
    57: ('calendario: la planificacion ocurrio al abrir el sprint', 'una por sprint', 'proxy'),
    58: ('calendario: la reunion diaria ocurrio', 'una por dia habil', 'proxy'),
    59: ('calendario: la revision ocurrio al cerrar el sprint', 'una por sprint', 'proxy'),
    60: ('calendario: la retrospectiva ocurrio al cerrar el sprint', 'una por sprint', 'proxy'),
    62: ('tablero: la estimacion pertenece a la escala', 'valor en la escala declarada', 'proxy'),

    84: ('git_checks.py --rule cadencia', 'hueco entre entregas <= 30 dias', 'instrumented'),
    85: ('repo_checks.py --rule e2', 'un comando corre toda la suite', 'instrumented'),
    86: ('repo_checks.py --rule g24', 'convenciones declaradas en verde', 'instrumented'),
    88: ('CI: corrida por commit con exit 0', 'sin commits sin integrar', 'instrumented'),

    104: ('repo_checks.py --rule t9 y --rule aislamiento', 'rapidas e independientes', 'instrumented'),
    105: ('checks.py --rule anatomia', 'al menos una asercion por prueba', 'instrumented'),
    107: ('git_checks.py --rule tddorden', 'el test entra antes que el codigo', 'instrumented'),
    108: ('repo_checks.py --rule e2', 'la suite completa en verde', 'instrumented'),
    109: ('git_checks.py --rule tddorden', 'el test entra antes que el codigo', 'instrumented'),
    110: ('repo_checks.py --rule e2', 'la suite completa en verde', 'instrumented'),

    118: ('test_command de integracion', 'exit 0', 'instrumented'),
    119: ('test_command de aceptacion', 'exit 0', 'instrumented'),
    120: ('test_command funcional', 'exit 0', 'instrumented'),
    121: ('test_command de sistema', 'exit 0', 'instrumented'),
    122: ('git_checks.py --rule repounico', 'ninguna rama con commits sin integrar', 'instrumented'),

    140: ('checks.py --rule g12', 'cero variables asignadas y nunca leidas', 'instrumented'),
    142: ('checks.py --rule exprops', 'operadores por expresion <= 3', 'instrumented'),
    143: ('checks.py --rule metlineas', 'lineas por metodo <= 15', 'instrumented'),
    144: ('checks.py --rule g5', 'cero bloques duplicados', 'instrumented'),
    145: ('checks.py --rule g5', 'cero bloques duplicados entre clases hermanas', 'instrumented'),
    146: ('checks.py --rule g5', 'cero bloques duplicados entre clases sin parentesco', 'instrumented'),

    158: ('tablero: el proceso esta representado en columnas', 'todas las etapas visibles', 'proxy'),
    159: ('tablero: existe y refleja el flujo', 'una columna por etapa', 'proxy'),
    160: ('tablero: items simultaneos por columna', 'limite WIP declarado por columna', 'proxy'),
}

# Nombre canonico de la tecnica. Ver la nota en build_codigo_limpio.py.
ALIAS = {
    22: ['entrega temprana y continua', 'early and continuous delivery'],
    23: ['aceptar el cambio', 'welcome changing requirements'],
    24: ['entregas frecuentes', 'frequent delivery'],
    26: ['conversacion cara a cara', 'face to face conversation'],
    27: ['software funcionando como medida', 'working software is the measure'],
    28: ['ritmo sostenible', 'sustainable pace'],
    30: ['simplicidad', 'simplicity', 'maximize work not done'],
    32: ['inspeccionar y adaptar', 'inspect and adapt'],
    36: ['Product Owner', 'dueno de producto'],
    39: ['Scrum Master'],
    43: ['equipo de desarrollo', 'development team', 'Scrum Team'],
    47: ['backlog de producto', 'product backlog'],
    48: ['formato del item', 'backlog item format'],
    49: ['priorizacion del backlog', 'backlog ordering'],
    50: ['estimacion de esfuerzo', 'effort estimation', 'story points'],
    51: ['granularidad del item', 'right sizing'],
    52: ['criterios de aceptacion', 'acceptance criteria'],
    53: ['backlog de sprint', 'sprint backlog'],
    54: ['descomposicion en tareas', 'task breakdown'],
    55: ['incremento potencialmente entregable', 'potentially shippable increment'],
    57: ['planificacion de sprint', 'sprint planning'],
    58: ['reunion diaria', 'daily scrum', 'daily standup'],
    59: ['revision de sprint', 'sprint review'],
    60: ['retrospectiva', 'sprint retrospective'],
    62: ['T-shirt sizing', 'estimacion por tallas'],
    64: ['planning poker', 'scrum poker'],
    67: ['estimacion por columnas', 'affinity estimation'],
    68: ['estimacion por columnas y poker', 'affinity estimation'],
    78: ['cliente in-situ', 'on-site customer'],
    79: ['semana de 40 horas', '40 hour week', 'sustainable pace'],
    80: ['metafora', 'system metaphor'],
    81: ['diseno simple', 'simple design'],
    82: ['refactorizacion', 'refactoring'],
    83: ['programacion de a pares', 'pair programming'],
    84: ['entregas cortas', 'short releases'],
    85: ['testing', 'automated testing'],
    86: ['convenciones de codigo', 'coding standards'],
    87: ['propiedad colectiva', 'collective ownership'],
    88: ['integracion continua', 'continuous integration'],
    89: ['juego de planificacion', 'planning game'],
    95: ['code kata', 'codekata'],
    96: ['code kata', 'kata'],
    97: ['randori'],
    98: ['randori'],
    104: ['pruebas unitarias', 'unit tests', 'FIRST'],
    105: ['anatomia del test', 'arrange act assert'],
    107: ['red green refactor', 'test first'],
    108: ['hacer que pase', 'make it pass', 'green'],
    109: ['red green refactor', 'test first'],
    110: ['hacer que pase', 'make it pass', 'green'],
    118: ['test de integracion', 'integration tests'],
    119: ['test de aceptacion', 'acceptance tests'],
    120: ['test funcionales', 'functional tests'],
    121: ['test de sistema', 'system tests'],
    122: ['repositorio unico', 'single repository', 'mainline'],
    140: ['variable temporal', 'temporary variable'],
    141: ['parametro contra propiedad', 'parameter versus field'],
    142: ['variable explicativa', 'extract variable', 'expresiones extensas'],
    143: ['metodo extenso', 'long method', 'extract method'],
    144: ['DRY', 'duplicated code'],
    145: ['DRY', 'duplicated code', 'pull up method'],
    146: ['DRY', 'duplicated code'],
    158: ['visualizar el flujo', 'visualize the workflow'],
    159: ['tablero Kanban', 'kanban board'],
    160: ['limite WIP', 'work in progress limit'],
    161: ['optimizar el flujo', 'optimize flow', 'cycle time'],
}

# Pila B: tecnica real cuya propiedad definitoria no es medible.
B_NODES = {
    22, 23, 26, 27, 28, 30,
    36, 37, 39, 40, 43, 44, 51, 64, 65, 66, 67, 68,
    78, 79, 80, 81, 82, 83, 87, 89, 95, 96, 97, 98, 100,
    138, 141,
    152, 153,
    161,
}

# Por que no es contractable, solo donde la autora da la razon o donde el caso
# marca la frontera.
WHY_NOT = {
    79: ('pese al titulo, la autora no fija el numero: habla de no exigir mas '
         'esfuerzo del humanamente disponible, que es un juicio'),
    81: 'que un diseno sea "simple" es exactamente lo que no se puede medir',
    87: ('la autora la define como conocimiento compartido del equipo, no como '
         'reparto de autoria; el reparto se medira en git, el conocimiento no'),
    141: ('es una distincion de diseno entre parametro, variable temporal y '
          'propiedad de clase, no un umbral'),
    51: 'la granularidad correcta de un item depende del equipo y del contexto',
}

# Enlaces. Un destino con `/` apunta a otro libro del grafo.
LINKS = {
    24: [84],
    84: [24],
    85: ['{}/t1'.format(CL), '{}/e2'.format(CL)],
    86: ['{}/g24'.format(CL)],
    88: ['{}/e2'.format(CL), 122],
    104: ['{}/t9'.format(CL)],
    107: [108, 109, 110],
    108: [107],
    109: [107, 110],
    110: [109],
    122: [88],
    138: [140, 142, 143],
    140: ['{}/g12'.format(CL), 142],
    141: ['{}/f1'.format(CL)],
    142: ['{}/g19'.format(CL), 140],
    143: ['{}/g30'.format(CL)],
    144: ['{}/g5'.format(CL), 145, 146],
    145: ['{}/g5'.format(CL), 144],
    146: ['{}/g5'.format(CL), 144],
    160: [159],
    161: [160],
}

# El hallazgo que justifica que el grafo sea un grafo: la misma tecnica en
# pilas distintas segun si su autor la operacionalizo.
NOTA_CRUZADA = {
    142: ('Martin describe esta misma refactorizacion en G19 y la deja fuera de '
          'lo contractable: dice que conviene siempre mas y que es dificil '
          'excederse, o sea sin umbral, y ademas le exige nombres descriptivos. '
          'Bahit la deja contractable porque su ejemplo extrae las '
          'subexpresiones a variables llamadas `$a`, `$b`, `$c`, `$d`: al no '
          'reclamar nada del nombre, lo unico que queda de la tecnica es la '
          'reduccion de complejidad de la expresion, que es lo que un parser '
          'cuenta. La tecnica es la misma; lo que cambia es si el autor la '
          'aterrizo.'),
    143: ('El equivalente de Martin es G30 ("las funciones solo deben hacer una '
          'cosa"), que queda en pila B porque el cuenta operaciones semanticas '
          'y nunca da un numero. Bahit lo plantea como extension del metodo, '
          'que si tiene umbral.'),
}

_LINEA = re.compile(r'^\s*(\d+)\|\s*L(\d)\s*\|\s*(.+?)\s*\|\s*p(\d+)\s*$')


def slugify(text, maxlen=60):
    norm = unicodedata.normalize('NFKD', text)
    ascii_text = ''.join(c for c in norm if not unicodedata.combining(c)).lower()
    ascii_text = re.sub(r'[^a-z0-9]+', '-', ascii_text).strip('-')
    return ascii_text[:maxlen].rstrip('-') if len(ascii_text) > maxlen else ascii_text


def leer_marcadores(texto):
    entradas = {}
    for linea in texto.splitlines():
        m = _LINEA.match(linea)
        if m:
            entradas[int(m.group(1))] = (int(m.group(2)), m.group(3), int(m.group(4)))
    return entradas


def seccion_de(indice):
    for desde, hasta, nombre in SECCIONES:
        if desde <= indice <= hasta:
            return nombre
    return 'sin seccion'


def build(texto):
    entradas = leer_marcadores(texto)
    indices = [i for i in sorted(entradas) if i not in CONTENEDORES]

    faltan = [i for i in list(A_NODES) + sorted(B_NODES) if i not in entradas]
    if faltan:
        raise SystemExit('ERROR: indices del triaje que no existen en los '
                         'marcadores: {}'.format(faltan))

    id_por_indice = {}
    for indice in indices:
        _nivel, titulo, _pagina = entradas[indice]
        # El id es el indice del marcador y nada mas. Ver ADR abajo.
        id_por_indice[indice] = '{:03d}'.format(indice)

    def destino(objetivo):
        if isinstance(objetivo, str):
            return objetivo
        return id_por_indice.get(objetivo)

    nodes = []
    for indice in indices:
        _nivel, titulo, pagina = entradas[indice]
        seccion = seccion_de(indice)

        if indice in A_NODES:
            instrumento, umbral, verification = A_NODES[indice]
            pila = 'A'
        elif indice in B_NODES:
            instrumento = umbral = None
            pila, verification = 'B', 'none'
        else:
            instrumento = umbral = None
            pila, verification = 'C', 'none'

        tags = ['scrum-xp', slugify(seccion), {'A': 'contractable',
                                               'B': 'no-especificable',
                                               'C': 'conocimiento'}[pila]]
        if verification in ('instrumented', 'proxy'):
            tags.append(verification)

        node = {
            'id': id_por_indice[indice],
            'title': titulo,
            'description': '{} (seccion: {}).'.format(titulo, seccion),
            'type': 'Concept',
            'tags': tags,
            'pile': pila,
            'verification': verification,
            'locator': 'pagina {}'.format(pagina),
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
            'slug': 'scrum-xp',
            'title': 'Scrum y eXtreme Programming para Programadores',
            'author': 'Eugenia Bahit',
            'file': 'Scrum Extreme Programming Para Programadores (Bahit Eugenia).pdf',
            'pages': 162,
            'extracted_with': 'pymupdf (get_toc)',
            'tags': ['fuente', 'libro', 'scrum-xp'],
            'corpus': ('Los 161 marcadores que la autora dejo en el PDF, menos los 8 '
                       'contenedores de capitulo de nivel 1: 153 items.'),
        },
        'nodes': nodes,
    }, indices


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('toc', help='volcado de marcadores del PDF')
    parser.add_argument('-o', '--out', default=os.path.join('books', 'scrum-xp.json'))
    args = parser.parse_args(argv)

    with open(args.toc, 'r', encoding='utf-8') as fh:
        spec, indices = build(fh.read())

    os.makedirs(os.path.dirname(args.out) or '.', exist_ok=True)
    with open(args.out, 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(spec, fh, ensure_ascii=False, indent=2)
        fh.write('\n')

    total = len(spec['nodes'])
    pilas = {'A': 0, 'B': 0, 'C': 0}
    instr = 0
    for node in spec['nodes']:
        pilas[node['pile']] += 1
        if node['verification'] == 'instrumented':
            instr += 1
    print('OK: {} nodos -> {}'.format(total, args.out))
    print('  A={} ({:.1f}%)  B={}  C={}  | instrumented={} ({:.1f}%)'.format(
        pilas['A'], 100.0 * pilas['A'] / total, pilas['B'], pilas['C'],
        instr, 100.0 * instr / total))
    print('\n  fraccion instrumented por seccion (es lo que decide el ruteo):')
    for desde, hasta, nombre in SECCIONES:
        de_la_seccion = [i for i in indices if desde <= i <= hasta]
        con_instr = sum(1 for i in de_la_seccion
                        if i in A_NODES and A_NODES[i][2] == 'instrumented')
        print('    {:<38} {:>2}/{:<3} {:>5.1f}%'.format(
            nombre, con_instr, len(de_la_seccion),
            100.0 * con_instr / len(de_la_seccion)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
