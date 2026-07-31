#!/usr/bin/env python3
"""Construye books/pep8.json a partir de los titulos de PEP 8.

Septima fuente, y entro con dos predicciones escritas antes de triajar. La
primera se cumplio y la segunda **se equivoco**, que es lo que la hace valer la
pena.

**Prediccion 1: queda arriba de los libros de codigo.** PEP 8 es una guia de
estilo escrita para que la revise una herramienta, asi que si la
contractabilidad la decide la operacionalizacion mas el alcance del artefacto,
tenia que dar alto. Dio **69,0%**, el mas alto de las siete fuentes, por encima
del manifiesto (62,5%).

**Prediccion 2: iba a ser la primera fuente con reuso alto de instrumentos.**
Las seis anteriores obligaron a inventar familias nuevas, y esta habla del mismo
artefacto que Codigo Limpio —el AST y el texto de un archivo Python— con 22
reglas ya escritas esperando. Fallo: de sus 29 tecnicas medibles, **una sola**
reusa una regla existente.

Y el fallo deja el hallazgo mas util de esta fuente. `checks.py` mide
duplicacion, numeros magicos, codigo muerto, envidia de caracteristicas: habla
de **estructura y significado**. PEP 8 mide sangria, lineas en blanco, orden de
imports, CapWords: habla de **forma superficial**. Mismo lenguaje, mismo
artefacto, misma clase de prescripcion, y los instrumentos no se tocan. Lo que
no transfiere no es el idioma ni el artefacto: es **la propiedad que se mide**.

La unica coincidencia real es `repo_checks.py --rule g24`, que Martin llama
"seguir las convenciones estandar" y que ya media largo de linea, tabuladores y
espacios al final — o sea que G24 de Codigo Limpio ya era, sin decirlo, un
pedazo de PEP 8.

**Advertencia de corpus, y esta subestima en vez de sobreestimar.** El corpus
son titulos, y "Programming Recommendations" es un solo titulo que adentro trae
quince reglas concretas y medibles —comparar con `is None`, no usar `except`
pelado, `isinstance` en vez de comparar tipos—. Cuenta como un nodo y cae en
pila B porque una seccion cajon no tiene un umbral. Con un corpus por regla en
vez de por titulo, el 69% seria mas alto.

Entrada: el volcado de titulos, una linea por entrada:

    <indice>| H<nivel> | <ancla> | <titulo>

Uso:
    python build_pep8.py [books/pep8-toc.txt] [-o books/pep8.json]
"""

import argparse
import json
import os
import re
import sys

CL = 'codigo-limpio'

# (primer_indice, ultimo_indice, nombre)
SECCIONES = [
    (1, 2, 'preambulo'),
    (3, 11, 'disposicion del codigo'),
    (12, 16, 'espacios y comas'),
    (17, 20, 'comentarios'),
    (21, 37, 'nombres'),
    (38, 40, 'recomendaciones'),
    (41, 42, 'cierre'),
]

# Pila A: (instrumento, umbral). 29 de 42.
#
# Una sola reusa: `g24`, que ya media largo de linea, tabuladores y espacios al
# final. Las otras 28 nombran el instrumento que haria falta, igual que las 53
# de htmx y los doce factores en su momento.
A_NODES = {
    4: ('pep8_checks: sangria multiplo de cuatro espacios (sin implementar)',
        'cuatro espacios por nivel'),
    5: ('repo_checks.py --rule g24',
        'cero tabuladores de indentacion'),
    6: ('repo_checks.py --rule g24 --max-line 79',
        '79 caracteres, 72 para comentarios y docstrings'),
    7: ('pep8_checks: el corte de linea cae ANTES del operador binario '
        '(sin implementar)',
        'cero cortes despues del operador'),
    8: ('pep8_checks: lineas en blanco entre definiciones (sin implementar)',
        'dos entre definiciones de nivel superior, una entre metodos'),
    9: ('pep8_checks: el archivo decodifica como UTF-8 y no repite la '
        'declaracion de codificacion (sin implementar)',
        'UTF-8 sin cookie redundante'),
    10: ('pep8_checks: un import por linea, agrupados por origen, sin comodines '
         '(sin implementar)',
         'cero imports con comodin y cero grupos fuera de orden'),
    11: ('pep8_checks: los dunder de modulo van despues del docstring y antes de '
         'los imports (sin implementar)',
         'cero dunder fuera de lugar'),
    12: ('pep8_checks: cadenas que escapan una comilla pudiendo usar la otra '
         '(sin implementar)',
         'cero escapes evitables'),
    14: ('pep8_checks: espacios sobrantes dentro de parentesis y antes de coma o '
         'dos puntos (sin implementar)',
         'cero'),
    15: ('pep8_checks: un espacio a cada lado de los operadores, ninguno '
         'alrededor del `=` de un argumento con nombre (sin implementar)',
         'cero desviaciones'),
    16: ('pep8_checks: coma final en los literales que cierran en su propia '
         'linea (sin implementar)',
         'cero literales multilinea sin coma final'),
    18: ('pep8_checks: los comentarios de bloque empiezan con `# ` y se sangran '
         'al nivel del codigo (sin implementar)',
         'cero comentarios mal formados'),
    19: ('pep8_checks: dos espacios antes del `#` de un comentario en linea '
         '(sin implementar)',
         'cero comentarios en linea pegados al codigo'),
    20: ('pep8_checks: toda API publica tiene docstring y las multilinea cierran '
         'en su propia linea (sin implementar)',
         'cero publicas sin docstring'),
    25: ('pep8_checks: identificadores de un solo caracter `l`, `O` o `I` '
         '(sin implementar)',
         'cero'),
    26: ('pep8_checks: identificadores fuera de ASCII (sin implementar)',
         'cero'),
    27: ('pep8_checks: modulos en minusculas (sin implementar)',
         'cero nombres de modulo fuera de convencion'),
    28: ('pep8_checks: clases en CapWords (sin implementar)',
         'cero clases fuera de convencion'),
    29: ('pep8_checks: variables de tipo en CapWords, con sufijo de varianza '
         'cuando corresponde (sin implementar)',
         'cero variables de tipo fuera de convencion'),
    30: ('pep8_checks: las excepciones son clases en CapWords y terminan en '
         '"Error" (sin implementar)',
         'cero excepciones fuera de convencion'),
    31: ('pep8_checks: globales en minusculas con guion bajo (sin implementar)',
         'cero globales fuera de convencion'),
    32: ('pep8_checks: funciones y variables en minusculas con guion bajo '
         '(sin implementar)',
         'cero nombres fuera de convencion'),
    33: ('pep8_checks: `self` en los metodos de instancia y `cls` en los de '
         'clase (sin implementar)',
         'cero primeros argumentos mal nombrados'),
    34: ('pep8_checks: metodos y atributos en minusculas, con un guion bajo '
         'inicial los no publicos (sin implementar)',
         'cero fuera de convencion'),
    35: ('pep8_checks: constantes de modulo en mayusculas (sin implementar)',
         'cero constantes fuera de convencion'),
    37: ('pep8_checks: el modulo declara su superficie publica y prefija con '
         'guion bajo lo interno (sin implementar)',
         'toda API publica declarada'),
    39: ('pep8_checks: espacios alrededor de `->` y en los dos puntos de '
         'anotacion (sin implementar)',
         'cero anotaciones mal espaciadas'),
    40: ('pep8_checks: espacios en la anotacion de una asignacion '
         '(sin implementar)',
         'cero anotaciones mal espaciadas'),
}

# Pila C: lo que no es una tecnica. Titulos contenedores y cierre del documento.
C_INDICES = {1, 3, 13, 17, 21, 23, 24, 41, 42}

WHY_NOT = {
    2: ('es la seccion que dice cuando NO seguir la guia: "saber cuando ser '
        'inconsistente". Es una instruccion sobre el juicio, y una regla que '
        'midiera el juicio se contradeciria a si misma'),
    22: ('"los nombres visibles como parte publica deben reflejar el uso y no la '
         'implementacion" es exactamente el juicio que N1 y N2 de Codigo Limpio '
         'tampoco pueden medir'),
    36: ('decidir que atributos son publicos y cuales no es diseno, no forma. La '
         'convencion de nombres que se sigue DESPUES de decidirlo si se mide, y '
         'esa es la 34'),
    38: ('es un titulo cajon: adentro trae quince reglas concretas y medibles '
         '—comparar con `is None`, no usar `except` pelado, `isinstance` en vez '
         'de comparar tipos— y ninguna es "la seccion". Medirla como un solo '
         'nodo no significa nada, y es el lugar donde el corpus por titulo '
         'subestima a esta fuente'),
}

ALIAS = {
    2: ['consistencia insensata', 'foolish consistency'],
    4: ['sangria', 'indentation', 'cuatro espacios'],
    5: ['tabuladores o espacios', 'tabs or spaces'],
    6: ['largo de linea', 'maximum line length', '79 caracteres'],
    7: ['corte antes del operador', 'line break binary operator'],
    8: ['lineas en blanco', 'blank lines'],
    9: ['codificacion del archivo', 'source file encoding', 'utf-8'],
    10: ['orden de imports', 'imports', 'import comodin'],
    11: ['dunder de modulo', 'module level dunder names'],
    12: ['comillas', 'string quotes'],
    14: ['espacios sobrantes', 'pet peeves', 'whitespace'],
    15: ['espacios alrededor de operadores', 'other recommendations'],
    16: ['coma final', 'trailing commas'],
    18: ['comentarios de bloque', 'block comments'],
    19: ['comentarios en linea', 'inline comments'],
    20: ['docstrings', 'documentation strings'],
    22: ['principio superior de nombres', 'overriding principle'],
    25: ['nombres a evitar', 'names to avoid'],
    26: ['compatibilidad ascii', 'ascii compatibility'],
    27: ['nombres de modulo', 'package and module names'],
    28: ['nombres de clase', 'class names', 'CapWords'],
    29: ['variables de tipo', 'type variable names'],
    30: ['nombres de excepcion', 'exception names'],
    31: ['nombres de globales', 'global variable names'],
    32: ['nombres de funcion', 'function and variable names', 'snake_case'],
    33: ['argumentos de metodo', 'self y cls'],
    34: ['nombres de metodo', 'method names and instance variables'],
    35: ['constantes', 'constants'],
    36: ['disenar para la herencia', 'designing for inheritance'],
    37: ['superficie publica', 'public and internal interfaces', '__all__'],
    39: ['anotaciones de funcion', 'function annotations'],
    40: ['anotaciones de variable', 'variable annotations'],
}

# Enlaces cruzados. Esta fuente es la que mas cruza del grafo, y no por
# casualidad: habla del mismo artefacto que Codigo Limpio.
LINKS = {
    5: ['{}/g24'.format(CL)],
    6: ['{}/g24'.format(CL)],
    10: ['{}/j1'.format(CL), '{}/g12'.format(CL)],
    22: ['{}/n1'.format(CL), '{}/n2'.format(CL)],
    25: ['{}/n6'.format(CL)],
    32: ['{}/n5'.format(CL)],
    37: ['{}/g8'.format(CL)],
    18: [19, 20],
}

NOTA_CRUZADA = {
    6: ('G24 de Codigo Limpio se llama "seguir las convenciones estandar", y su '
        'instrumento ya media largo de linea, tabuladores y espacios al final. '
        'O sea que G24 **ya era un pedazo de PEP 8 sin decirlo**: Martin nombra '
        'la convencion y delega en el equipo cual es; PEP 8 es esa convencion '
        'escrita. Es la unica regla que las dos fuentes comparten de verdad.'),
    10: ('Aca los dos autores se contradicen, y el grafo lo sostiene sin elegir. '
         'J1 de Codigo Limpio aconseja **usar imports con comodin** para evitar '
         'listas largas; PEP 8 los prohibe porque borran que nombres entran al '
         'espacio de nombres. J1 esta en el grafo sin instrumento por ese '
         'motivo: implementarla invirtiendo el consejo seria tergiversar al '
         'autor. Con esta fuente adentro, la contradiccion deja de ser una nota '
         'al pie y pasa a ser un enlace: dos nodos, dos autores, umbrales '
         'opuestos sobre el mismo artefacto.'),
    25: ('N6 de Codigo Limpio ("evitar codificaciones") y esta son la misma '
         'familia de defecto —un nombre que no se puede leer— por dos motivos '
         'distintos: Martin habla de prefijos que codifican el tipo, PEP 8 de '
         'caracteres que se confunden con digitos en la pantalla. Las dos son '
         'medibles y necesitan instrumentos distintos.'),
    37: ('G8 de Codigo Limpio mide el exceso de superficie publica y esta pide '
         'que la superficie **este declarada**. Son complementarias y las dos '
         'terminan mirando `__all__`, que es tambien lo que `check_g9` exige '
         'antes de hablar de codigo muerto: sin saber que es publico, no se '
         'puede decir que sobra.'),
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


def build(texto):
    entradas = leer(texto)
    faltan = [i for i in list(A_NODES) + sorted(C_INDICES) if i not in entradas]
    if faltan:
        raise SystemExit('ERROR: indices del triaje que no existen: {}'.format(faltan))

    ids = {i: 's{:02d}'.format(i) for i in entradas}

    def destino(t):
        return t if isinstance(t, str) else ids.get(t)

    nodes = []
    for indice in sorted(entradas):
        nivel, ancla, titulo = entradas[indice]
        seccion = seccion_de(indice)
        if indice in A_NODES:
            pila, verification = 'A', 'instrumented'
            instrumento, umbral = A_NODES[indice]
        elif indice in C_INDICES:
            pila, verification, instrumento, umbral = 'C', 'none', None, None
        else:
            pila, verification, instrumento, umbral = 'B', 'none', None, None

        tags = ['pep8', seccion.replace(' ', '-'),
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
            'locator': 'PEP 8, #{}'.format(ancla),
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
            'slug': 'pep8',
            'title': 'PEP 8 - Style Guide for Python Code',
            'author': 'Guido van Rossum, Barry Warsaw y Alyssa Coghlan',
            'file': 'peps.python.org/pep-0008',
            'pages': 0,
            'extracted_with': 'titulos del documento, verificados contra la fuente',
            'tags': ['fuente', 'guia-de-estilo', 'python'],
            'corpus': ('Los 42 titulos de seccion del documento, con su nivel de '
                       'anidacion. EL CORPUS SUBESTIMA A ESTA FUENTE, al reves que en '
                       'las otras seis: "Programming Recommendations" es un solo '
                       'titulo que adentro trae quince reglas concretas y medibles, y '
                       'cuenta como un nodo. Con un corpus por regla en vez de por '
                       'titulo, el porcentaje seria mas alto.'),
        },
        'nodes': nodes,
    }, entradas


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('toc', nargs='?', default=os.path.join('books', 'pep8-toc.txt'))
    parser.add_argument('-o', '--out', default=os.path.join('books', 'pep8.json'))
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
    reusa = sum(1 for n in spec['nodes']
                if n['pile'] == 'A' and n['instrument'].split()[0].endswith('.py'))
    print('OK: {} nodos -> {}'.format(total, args.out))
    print('  A={} ({:.1f}%)  B={}  C={}'.format(
        pilas['A'], 100.0 * pilas['A'] / total, pilas['B'], pilas['C']))
    print('  reusan un instrumento que ya existia: {} de {}'.format(reusa, pilas['A']))
    for desde, hasta, nombre in SECCIONES:
        de_la = [i for i in entradas if desde <= i <= hasta]
        a = sum(1 for i in de_la if i in A_NODES)
        print('    {:<24} {}/{:<3} {:>5.1f}%'.format(
            nombre, a, len(de_la), 100.0 * a / len(de_la)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
