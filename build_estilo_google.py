#!/usr/bin/env python3
"""Construye books/estilo-google.json a partir de los titulos de la guia de Google.

Octava fuente, y entro para **aislar una variable**. PEP 8 dio 69,0%, el mas alto
de las siete, y la explicacion que el grafo venia dando era el genero: una guia
de estilo escrita para que la revise una herramienta. Pero PEP 8 cambia dos
cosas a la vez respecto de los libros — el genero Y el tipo de propiedad, que en
su caso es forma superficial de un archivo.

Esta fuente deja el genero fijo (es otra guia de estilo), deja el artefacto al
alcance (texto plano, tan legible como un `.py`) y cambia **el dominio de la
propiedad**: aca se prescribe sobre prosa.

**La prediccion, escrita antes de triajar, fue que caeria entre 20% y 45%**, muy
por debajo de PEP 8, porque las reglas de prosa parecian repartirse entre
lexicas y de registro. **Fallo.** Dio **52,5%**, arriba de Codigo Limpio.

Y el fallo es el hallazgo. Al contar seccion por seccion se ve por que: la mayor
parte de una guia de estilo —de codigo o de prosa— **no prescribe sobre el
significado, prescribe sobre tipografia y vocabulario**. Coma serial, guion largo
sin espacios, cero "and/or", cero "(s)", segunda persona, presente, encabezados
en minuscula, unidades separadas del numero. Todo eso es lexico, y lo lexico se
mide. Lo que no se mide es lo que pide juzgar sentido: "voz y tono", "audiencia
global", "evitar el antropomorfismo", "parrafos cortos".

Asi que el genero no era el motor, era un correlato: **las guias de estilo
tienden a prescribir propiedades lexicas**, y por eso quedan arriba. Lo que
ordena la distribucion es la NATURALEZA DE LA PROPIEDAD — lexica o estructural
contra semantica— y eso vale igual sobre un `.py` que sobre un `.md`.

Entrada: el volcado de titulos, una linea por entrada:

    <indice>| H<nivel> | <grupo> | <titulo>

Uso:
    python build_estilo_google.py [books/estilo-google-toc.txt] [-o books/estilo-google.json]
"""

__all__ = ['build', 'leer', 'main', 'seccion_de']

import argparse
import json
import os
import re
import sys

P8 = 'pep8'
WC = 'wcag'

SECCIONES = [
    (1, 5, 'introduccion'),
    (6, 9, 'recursos'),
    (10, 20, 'principios generales'),
    (21, 35, 'lengua y gramatica'),
    (36, 46, 'puntuacion'),
    (47, 62, 'formato'),
    (63, 65, 'enlaces'),
    (66, 72, 'interfaces'),
    (73, 76, 'html'),
    (77, 80, 'nombres'),
]

# Pila A: (instrumento, umbral). 42 de 80.
#
# Todas leen el mismo artefacto —el texto del documento— y ninguna esta escrita
# todavia: se nombra el instrumento que haria falta, como con htmx antes de
# `template_checks`. Las que dicen "(lista declarada)" necesitan que el proyecto
# declare su vocabulario, igual que `arch_checks` pide las capas: la guia trae
# la suya, pero cada proyecto tiene la propia.
A_NODES = {
    7: ('prosa_checks: terminos fuera de la lista de palabras declarada '
        '(sin implementar, lista declarada)',
        'cero terminos desaconsejados'),
    8: ('prosa_checks: nombres de producto escritos como los declara el proyecto '
        '(sin implementar, lista declarada)',
        'cero nombres de producto mal escritos'),
    12: ('prosa_checks: adjetivos que minimizan el esfuerzo ("simply", "just", '
         '"easy") (sin implementar)',
         'cero'),
    15: ('prosa_checks: terminos no inclusivos de la lista declarada '
         '(sin implementar, lista declarada)',
         'cero'),
    16: ('prosa_checks: jerga de la lista declarada (sin implementar, lista declarada)',
         'cero'),
    19: ('prosa_checks: marcas de tiempo relativas ("currently", "new", "soon") '
         '(sin implementar)',
         'cero'),
    22: ('prosa_checks: abreviaturas latinas ("e.g.", "i.e.", "etc.") '
         '(sin implementar)',
         'cero'),
    26: ('prosa_checks: encabezados y titulos en minuscula de oracion '
         '(sin implementar)',
         'cero encabezados fuera de convencion'),
    28: ('prosa_checks: plurales escritos "(s)" (sin implementar)',
         'cero'),
    29: ('prosa_checks: posesivo sobre un nombre de producto '
         '(sin implementar, lista declarada)',
         'cero'),
    31: ('prosa_checks: tiempo futuro ("will") fuera de las excepciones '
         '(sin implementar)',
         'cero'),
    32: ('prosa_checks: pronombres de genero ("he", "she", "his", "her") '
         '(sin implementar)',
         'cero'),
    33: ('prosa_checks: primera persona ("we", "our", "us") en instrucciones '
         '(sin implementar)',
         'cero'),
    37: ('prosa_checks: mayuscula despues de dos puntos solo si sigue una oracion '
         'completa (sin implementar)',
         'cero desviaciones'),
    38: ('prosa_checks: coma serial en toda enumeracion de tres o mas '
         '(sin implementar)',
         'cero enumeraciones sin coma serial'),
    39: ('prosa_checks: raya larga sin espacios alrededor (sin implementar)',
         'cero rayas mal espaciadas'),
    40: ('prosa_checks: puntos suspensivos escritos con tres puntos sueltos '
         '(sin implementar)',
         'cero'),
    42: ('prosa_checks: parentesis anidados (sin implementar)',
         'cero'),
    43: ('prosa_checks: un espacio despues del punto y cero puntos al final de un '
         'encabezado (sin implementar)',
         'cero desviaciones'),
    44: ('prosa_checks: coma y punto adentro de las comillas (sin implementar)',
         'cero desviaciones'),
    46: ('prosa_checks: "and/or" y la barra usada como "o" (sin implementar)',
         'cero'),
    48: ('prosa_checks: fechas en el formato declarado y sin ordinales '
         '(sin implementar)',
         'cero fechas fuera de formato'),
    50: ('prosa_checks: toda imagen tiene texto alternativo (sin implementar)',
         'cero imagenes sin alt'),
    51: ('prosa_checks: notas al pie (sin implementar)',
         'cero'),
    52: ('prosa_checks: encabezados unicos, en minuscula de oracion y sin punto '
         'final (sin implementar)',
         'cero encabezados fuera de convencion'),
    54: ('prosa_checks: items de lista con mayuscula inicial y puntuacion '
         'coherente (sin implementar)',
         'cero listas incoherentes'),
    55: ('prosa_checks: notacion matematica en el formato declarado '
         '(sin implementar)',
         'cero expresiones fuera de formato'),
    56: ('prosa_checks: los avisos usan uno de los tipos declarados '
         '(sin implementar, lista declarada)',
         'cero avisos de tipo inventado'),
    57: ('prosa_checks: numeros menores a diez escritos con letra fuera de '
         'medidas (sin implementar)',
         'cero numeros fuera de convencion'),
    59: ('prosa_checks: telefonos de ejemplo del rango reservado '
         '(sin implementar)',
         'cero telefonos reales'),
    60: ('prosa_checks: los procedimientos son listas numeradas y cada paso '
         'empieza con un verbo (sin implementar)',
         'cero pasos que no empiecen con verbo'),
    61: ('prosa_checks: toda tabla tiene fila de encabezado (sin implementar)',
         'cero tablas sin encabezado'),
    62: ('prosa_checks: espacio entre el numero y la unidad (sin implementar)',
         'cero unidades pegadas'),
    64: ('prosa_checks: texto de enlace descriptivo, cero "click here" y cero URL '
         'desnudas (sin implementar)',
         'cero enlaces sin texto util'),
    65: ('prosa_checks: todo enlace interno apunta a un encabezado que existe '
         '(sin implementar)',
         'cero anclas rotas'),
    69: ('prosa_checks: largo de linea de los bloques de codigo y cero elisiones '
         'con puntos suspensivos (sin implementar)',
         'cero lineas de codigo fuera de largo'),
    70: ('prosa_checks: la sintaxis de linea de comandos usa la convencion '
         'declarada para opcional y repetible (sin implementar)',
         'cero desviaciones'),
    71: ('prosa_checks: los marcadores de posicion usan el formato declarado '
         '(sin implementar)',
         'cero marcadores fuera de formato'),
    72: ('prosa_checks: verbos de interaccion prohibidos ("click on", "hit", '
         '"press") (sin implementar)',
         'cero'),
    76: ('prosa_checks: HTML crudo dentro de un documento Markdown '
         '(sin implementar)',
         'cero'),
    78: ('prosa_checks: dominios y nombres de ejemplo del rango reservado '
         '(sin implementar)',
         'cero ejemplos con dominios reales'),
    79: ('prosa_checks: nombres de archivo en minusculas y con guiones '
         '(sin implementar)',
         'cero nombres fuera de convencion'),
}

# Pila C: titulos de grupo y paginas sobre la guia misma.
C_INDICES = {1, 2, 3, 4, 5, 6, 9, 10, 21, 36, 47, 63, 66, 73, 77}

WHY_NOT = {
    11: ('escribir accesible es mucho mas que poner un `alt`: es decidir si el '
         'texto se entiende sin ver la figura. La mitad medible ya esta en la 50'),
    14: ('"escribir para una audiencia global" pide reconocer modismos y '
         'referencias culturales, que es entender el texto y no contarlo'),
    23: ('la guia pide voz activa "todo lo posible" y admite la pasiva cuando el '
         'agente no importa. Sin umbral no hay regla: detectar pasivas es facil, '
         'decidir cuales sobran no'),
    24: ('el antropomorfismo es una figura, no una palabra. "El sistema quiere" y '
         '"el sistema espera" difieren en sentido, no en forma'),
    25: ('la eleccion entre "a" y "an" va por SONIDO y no por letra, y la de '
         'usar articulo o no depende de que se este nombrando'),
    27: ('dice usar contracciones "cuando suenen naturales". Es registro, y el '
         'registro no tiene umbral'),
    30: ('la seccion desarma un mito —que no se puede terminar en preposicion— y '
         'lo que queda es criterio de lectura'),
    34: ('"oraciones cortas y claras" sin numero. Contar palabras seria inventar '
         'un umbral que el autor no dio'),
    35: ('depende de saber que el documento ES una referencia, y eso no esta en '
         'el texto'),
    41: ('la guia hifena "cuando ayuda a la claridad". Las dos reglas mecanicas '
         '—nada de guion tras un adverbio en -ly, prefijos comunes sin guion— son '
         'una parte, y confundir la parte con la seccion daria verde de mas'),
    45: ('recomienda preferir dos oraciones, sin prohibir el punto y coma'),
    49: ('"escribir ejemplos utiles" es juicio. La parte mecanica —usar dominios '
         'reservados— es la 78, y esta contada ahi'),
    53: ('hay que saber que una palabra es un TERMINO que se introduce, y eso es '
         'una decision sobre el contenido'),
    58: ('parrafos cortos, sin numero'),
    67: ('escribir buenos comentarios de referencia es la misma clase de juicio '
         'que N1 de Codigo Limpio: se mide que esten, no que sirvan'),
    68: ('pide poner en fuente de codigo lo que ES codigo, y decidir eso en medio '
         'de una oracion es entender la oracion'),
    74: ('"usar la etiqueta semantica correcta" pide saber que significa el '
         'contenido; es el mismo limite que 1.3.1 de WCAG'),
    75: ('convenciones de sangria y quiebre para HTML escrito a mano, que en un '
         'flujo de Markdown casi no aparece'),
    80: ('el uso correcto de una marca depende de la relacion legal con su duenio, '
         'que no esta en el documento'),
}

ALIAS = {
    8: ['nombres de producto', 'product names'],
    29: ['posesivos', 'possessives'],
    37: ['dos puntos', 'colons'],
    39: ['raya', 'guion largo', 'dashes', 'em dash'],
    40: ['puntos suspensivos', 'ellipses'],
    42: ['parentesis', 'parentheses'],
    43: ['punto final', 'periods', 'end punctuation'],
    44: ['comillas', 'quotation marks'],
    48: ['fechas y horas', 'dates and times'],
    51: ['notas al pie', 'footnotes'],
    55: ['notacion matematica', 'mathematical notation'],
    56: ['avisos', 'notes and other notices', 'callouts'],
    59: ['telefonos de ejemplo', 'phone numbers'],
    61: ['tablas', 'tables'],
    65: ['anclas de encabezado', 'headings as link targets'],
    70: ['sintaxis de linea de comandos', 'command-line syntax'],
    7: ['lista de palabras', 'word list', 'terminologia'],
    11: ['accesibilidad', 'accessibility'],
    12: ['claims excesivos', 'excessive claims', 'simply', 'just'],
    15: ['lenguaje inclusivo', 'inclusive language'],
    16: ['jerga', 'jargon'],
    19: ['documentacion sin fecha', 'timeless documentation'],
    22: ['abreviaturas', 'abbreviations'],
    23: ['voz activa', 'active voice'],
    26: ['mayusculas', 'capitalization', 'sentence case'],
    28: ['pluralizacion', 'pluralization'],
    31: ['presente', 'present tense'],
    32: ['pronombres', 'pronouns'],
    33: ['segunda persona', 'second person'],
    38: ['coma serial', 'serial comma', 'oxford comma'],
    46: ['and/or', 'barras', 'slashes'],
    50: ['texto alternativo', 'alt text', 'figures'],
    52: ['encabezados', 'headings and titles'],
    54: ['listas', 'lists'],
    57: ['numeros', 'numbers'],
    60: ['procedimientos', 'procedures', 'pasos numerados'],
    62: ['unidades', 'units of measurement'],
    64: ['texto de enlace', 'link text', 'click here'],
    69: ['ejemplos de codigo', 'code samples'],
    71: ['marcadores de posicion', 'placeholder formatting'],
    72: ['elementos de interfaz', 'ui elements', 'click on'],
    76: ['markdown contra html', 'markdown versus html'],
    78: ['dominios de ejemplo', 'example domains'],
    79: ['nombres de archivo', 'filenames'],
}

LINKS = {
    50: ['{}/sc1-1-1'.format(WC)],
    69: ['{}/s06'.format(P8)],
    79: ['{}/s27'.format(P8)],
    26: [52],
    74: ['{}/sc1-1-1'.format(WC)],
}

NOTA_CRUZADA = {
    50: ('El mismo `alt` en dos fuentes y en dos pilas. WCAG 1.1.1 pide una '
         'alternativa textual que cumpla **el proposito equivalente**, y la '
         'equivalencia no la decide ninguna medicion: por eso esta en pila B. '
         'Google pide que la imagen **tenga** texto alternativo, que es presencia '
         'y se cuenta. No es que una guia sea mejor: la que nombra el mecanismo '
         'se puede instrumentar, y la que nombra la cualidad no. Es el mismo par '
         'que htmx/20 con el criterio de teclado.'),
    69: ('El largo de linea de un bloque de codigo dentro de la documentacion es '
         'el mismo umbral que PEP 8 pone sobre el archivo, y lo mide el mismo '
         'tipo de instrumento. Cambia el envase, no la medicion — que es la '
         'excepcion que confirma el hallazgo 3: aca la propiedad SI es la misma.'),
    79: ('Minusculas y guiones para nombrar un archivo, dicho por dos autores '
         'sobre dos clases de archivo. Las dos son medibles por el mismo motivo: '
         'el nombre esta a la vista y la convencion es cerrada.'),
}

_LINEA = re.compile(r'^\s*(\d+)\|\s*H(\d)\s*\|\s*(\S+)\s*\|\s*(.+?)\s*$')


def leer(texto):
    """Indexa el volcado de titulos por numero de entrada."""
    out = {}
    for linea in texto.splitlines():
        if linea.lstrip().startswith('#'):
            continue
        m = _LINEA.match(linea)
        if m:
            out[int(m.group(1))] = (int(m.group(2)), m.group(3), m.group(4))
    return out


def seccion_de(indice):
    """La seccion del documento a la que pertenece un indice."""
    for desde, hasta, nombre in SECCIONES:
        if desde <= indice <= hasta:
            return nombre
    return 'sin seccion'


def build(texto):
    """Arma el spec de la fuente a partir del volcado de titulos."""
    entradas = leer(texto)
    faltan = [i for i in list(A_NODES) + sorted(C_INDICES) if i not in entradas]
    if faltan:
        raise SystemExit('ERROR: indices del triaje que no existen: {}'.format(faltan))

    ids = {i: 'e{:02d}'.format(i) for i in entradas}

    def destino(t):
        """Resuelve un enlace: texto si va a otra fuente, indice si es local."""
        return t if isinstance(t, str) else ids.get(t)

    nodes = []
    for indice in sorted(entradas):
        nivel, grupo, titulo = entradas[indice]
        seccion = seccion_de(indice)
        if indice in A_NODES:
            pila, verification = 'A', 'instrumented'
            instrumento, umbral = A_NODES[indice]
        elif indice in C_INDICES:
            pila, verification, instrumento, umbral = 'C', 'none', None, None
        else:
            pila, verification, instrumento, umbral = 'B', 'none', None, None

        tags = ['estilo-google', seccion.replace(' ', '-'),
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
            'locator': 'developers.google.com/style ({})'.format(grupo),
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
            'slug': 'estilo-google',
            'title': 'Google developer documentation style guide',
            'author': 'Google',
            'file': 'developers.google.com/style',
            'pages': 0,
            'extracted_with': 'navegacion del sitio, verificada contra la fuente',
            'tags': ['fuente', 'guia-de-estilo', 'prosa'],
            'corpus': ('Los 10 grupos de la navegacion y las 70 paginas que cuelgan '
                       'de ellos. Cada pagina es una seccion con sus propias reglas, '
                       'asi que el corpus por titulo subestima igual que en PEP 8: '
                       '"Commas" es un titulo y adentro trae media docena de reglas.'),
        },
        'nodes': nodes,
    }, entradas


def main(argv=None):
    """Lee el volcado de titulos, arma el JSON de la fuente y lo escribe."""
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('toc', nargs='?',
                        default=os.path.join('books', 'estilo-google-toc.txt'))
    parser.add_argument('-o', '--out',
                        default=os.path.join('books', 'estilo-google.json'))
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
    for desde, hasta, nombre in SECCIONES:
        de_la = [i for i in entradas if desde <= i <= hasta]
        a = sum(1 for i in de_la if i in A_NODES)
        print('    {:<22} {}/{:<3} {:>5.1f}%'.format(
            nombre, a, len(de_la), 100.0 * a / len(de_la)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
