#!/usr/bin/env python3
"""Construye books/arquitectura-java.json.

Tercer libro del grafo: "Arquitectura Java solida" (Cecilio Alvarez Caules).

**Advertencia de corpus, y hay que leerla antes que el numero.** Los otros dos
libros tienen una lista cerrada del autor: el catalogo enumerado del capitulo 17
en Codigo Limpio, los 161 marcadores del PDF en Scrum y XP. Este es un tutorial
progresivo que construye una sola aplicacion; sus secciones "Resumen" son prosa
narrativa y sus listas enumeradas son objetivos del ejemplo ("crear la pagina
InsertarLibro.jsp"), no tecnicas. El corpus de abajo son los 33 elementos
nombrados en los titulos de capitulo, identificados por el triaje y no
entregados por el autor. n es menor y la enumeracion es mas debil, asi que la
fraccion medida tiene barras de error mas anchas que las de los otros dos.

Se mantiene la consistencia de los otros libros: las tecnologias (HTML, JSP,
Hibernate, JSF...) se cuentan en pila C, no se descartan. Descartarlas inflaria
el resultado.

El hallazgo de este libro es que **la contractabilidad no la decide la tecnica
ni el dominio, sino si el autor la operacionalizo**. SRP aca y G30 en Codigo
Limpio son el mismo principio con destinos opuestos: Martin cuenta operaciones
semanticas y nunca da un numero; Caules lo aplica como separacion de capas, que
es una regla de imports.

Uso:
    python build_arquitectura_java.py [-o books/arquitectura-java.json]
"""

import argparse
import json
import os
import re
import sys
import unicodedata

CL = 'codigo-limpio'
SXP = 'scrum-xp'

# (indice, titulo, pila). El indice fija el orden del libro y el prefijo del id.
# A = existe una medicion determinista sobre el codigo cuyo umbral ES la
# tecnica. Las 15 de este libro son instrumented: todas se leen del grafo de
# imports, del de instanciacion o del AST. Ninguna depende de un registro que
# llene una persona, que es lo que separa a este libro de Scrum y XP.
ITEMS = [
    (1, 'Introduccion y entorno de desarrollo', 'C'),
    (2, 'HTML', 'C'),
    (3, 'Java Server Pages', 'C'),
    (4, 'El principio DRY', 'A'),
    (5, 'Editar, borrar y filtrar', 'C'),
    (6, 'Manejo de excepciones', 'A'),
    (7, 'Log4J', 'C'),
    (8, 'El principio SRP', 'A'),
    (9, 'El modelo MVC', 'A'),
    (10, 'JSTL', 'C'),
    (11, 'El principio OCP', 'A'),
    (12, 'El modelo MVC 2', 'A'),
    (13, 'El patron Command', 'B'),
    (14, 'Hibernate', 'C'),
    (15, 'Java Persistence API', 'C'),
    (16, 'El principio ISP', 'A'),
    (17, 'El patron DAO', 'A'),
    (18, 'El patron GenericDAO', 'A'),
    (19, 'El principio de inversion de control', 'A'),
    (20, 'El patron Factory', 'A'),
    (21, 'El patron Abstract Factory', 'B'),
    (22, 'La capa de servicio', 'A'),
    (23, 'La inyeccion de dependencia', 'A'),
    (24, 'El patron Template', 'B'),
    (25, 'Spring Templates y JDBCDAOSupport', 'C'),
    (26, 'Programacion orientada a aspectos', 'A'),
    (27, 'Proxies con Spring', 'C'),
    (28, 'El principio COC', 'A'),
    (29, 'Java Server Faces', 'C'),
    (30, 'Migracion a Java Server Faces', 'C'),
    (31, 'Servicios web y JAX-WS', 'C'),
    (32, 'Administracion y pools de conexiones', 'C'),
    (33, 'Conclusiones', 'C'),
]

# Instrumento y umbral de cada tecnica contractable.
INSTRUMENTOS = {
    4: ('checks.py --rule g5', 'cero bloques duplicados'),
    6: ('AST: clausulas catch vacias o demasiado amplias', 'cero catch mudos'),
    8: ('grafo de imports: la capa de presentacion no importa persistencia',
        'cero imports que crucen capas'),
    9: ('grafo de imports: vista, controlador y modelo separados',
        'cero imports que crucen capas'),
    11: ('checks.py --rule g23', 'cero cadenas if/else sobre un discriminante'),
    12: ('grafo de imports: el controlador no conoce la vista concreta',
         'cero imports que crucen capas'),
    16: ('AST: metodos usados por el cliente sobre metodos de la interfaz',
         'cero metodos de los que se depende sin usar'),
    17: ('grafo de imports: la persistencia solo se toca via DAO',
         'cero accesos a persistencia fuera de la capa DAO'),
    18: ('checks.py --rule g5', 'cero duplicacion entre los DAO'),
    19: ('AST: instanciacion de colaboradores dentro de la clase',
         'cero `new` de colaboradores'),
    20: ('AST: instanciacion de colaboradores fuera de las factorias',
         'cero `new` de colaboradores fuera de la factoria'),
    22: ('grafo de imports: la presentacion pasa por servicio y no por DAO',
         'cero imports que salteen la capa de servicio'),
    23: ('AST: instanciacion de colaboradores dentro de la clase',
         'cero dependencias asignadas por la propia clase'),
    26: ('AST: codigo transversal dentro de las clases de negocio',
         'cero logging ni transacciones en el negocio'),
    28: ('comparacion entre campos de la clase y columnas de la tabla',
         'los nombres coinciden sin configuracion'),
}

WHY_NOT = {
    13: ('la presencia de un patron no se detecta de forma robusta: una jerarquia '
         'con despacho puede ser Command o cualquier otra cosa'),
    21: 'lo mismo que Command, y ademas la capa extra sobre las factorias es un juicio',
    24: ('que el paso variable este bien elegido es exactamente la parte que no se '
         'puede medir'),
}

LINKS = {
    4: ['{}/g5-duplicacion'.format(CL), '{}/144-codigo-duplicado-en-una-misma-clase'.format(SXP), 18],
    8: ['{}/g30-las-funciones-solo-deben-hacer-una-cosa'.format(CL), 9, 22],
    9: [8, 12, 22],
    11: ['{}/g23-polimorfismo-antes-que-if-else-o-switch-case'.format(CL), 13],
    12: [9],
    13: [11],
    16: ['{}/g8-exceso-de-informacion'.format(CL), 17],
    17: [16, 18, 22],
    18: [4, 17],
    19: [20, 23],
    20: [19, 21],
    21: [20],
    22: [8, 17],
    23: [19],
    24: [26],
    26: [24],
}

NOTA_CRUZADA = {
    8: ('SRP y G30 de Codigo Limpio ("las funciones solo deben hacer una cosa") '
        'son el mismo principio, y quedan en pilas distintas. Martin nunca lo '
        'aterriza: cuenta operaciones semanticas y no da un numero, asi que su '
        'nodo queda en pila B. Caules lo aplica como separacion de capas — la '
        'JSP no contiene codigo de persistencia — y eso es una regla de imports '
        'que un checker de dependencias verifica. La contractabilidad no la '
        'decide la tecnica ni el dominio: la decide si el autor la '
        'operacionalizo.'),
    11: ('Caules no deja OCP en "abierto a extension, cerrado a modificacion": lo '
         'convierte en una prueba ejecutable — si agregar una funcionalidad '
         'obliga a tocar el controlador y sumarle un if/else, no se cumple. Eso '
         'es exactamente `touch_only` de un contrato KDD, y ademas coincide con '
         'la heuristica G23 de Martin.'),
    4: ('Tercera aparicion de la misma tecnica en el grafo. Los tres autores la '
        'operacionalizan, y por eso los tres nodos son contractables y comparten '
        'instrumento.'),
}


def slugify(text, maxlen=52):
    norm = unicodedata.normalize('NFKD', text)
    ascii_text = ''.join(c for c in norm if not unicodedata.combining(c)).lower()
    ascii_text = re.sub(r'[^a-z0-9]+', '-', ascii_text).strip('-')
    return ascii_text[:maxlen].rstrip('-') if len(ascii_text) > maxlen else ascii_text


def build():
    id_por_indice = {i: '{:02d}-{}'.format(i, slugify(t)) for i, t, _ in ITEMS}

    def destino(objetivo):
        return objetivo if isinstance(objetivo, str) else id_por_indice.get(objetivo)

    nodes = []
    for indice, titulo, pila in ITEMS:
        verification = 'instrumented' if pila == 'A' else 'none'
        tags = ['arquitectura-java', {'A': 'contractable',
                                      'B': 'no-especificable',
                                      'C': 'conocimiento'}[pila]]
        if pila == 'A':
            tags.append('instrumented')

        node = {
            'id': id_por_indice[indice],
            'title': titulo,
            'description': '{} (capitulo {} del libro).'.format(titulo, indice),
            'type': 'Concept',
            'tags': tags,
            'pile': pila,
            'verification': verification,
            'locator': 'capitulo {}'.format(indice),
            'links': [d for d in (destino(t) for t in LINKS.get(indice, [])) if d],
        }
        if indice in INSTRUMENTOS:
            node['instrument'], node['threshold'] = INSTRUMENTOS[indice]
        if indice in WHY_NOT:
            node['why_not'] = WHY_NOT[indice]
        if indice in NOTA_CRUZADA:
            node['body'] = NOTA_CRUZADA[indice]
        nodes.append(node)

    return {
        'source': {
            'slug': 'arquitectura-java',
            'title': 'Arquitectura Java solida',
            'author': 'Cecilio Alvarez Caules',
            'file': 'Arquitectura JAVA solida.pdf',
            'pages': 405,
            'extracted_with': 'pymupdf',
            'tags': ['fuente', 'libro', 'arquitectura-java'],
            'corpus': ('Los 33 elementos nombrados en los titulos de capitulo. '
                       'CORPUS MAS DEBIL que el de los otros dos libros: este es un '
                       'tutorial progresivo, no tiene lista cerrada de conclusiones '
                       'del autor, y la enumeracion la produjo el triaje. n es menor '
                       'y la fraccion medida tiene barras de error mas anchas.'),
        },
        'nodes': nodes,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('-o', '--out',
                        default=os.path.join('books', 'arquitectura-java.json'))
    args = parser.parse_args(argv)

    spec = build()
    os.makedirs(os.path.dirname(args.out) or '.', exist_ok=True)
    with open(args.out, 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(spec, fh, ensure_ascii=False, indent=2)
        fh.write('\n')

    total = len(spec['nodes'])
    pilas = {'A': 0, 'B': 0, 'C': 0}
    for node in spec['nodes']:
        pilas[node['pile']] += 1
    print('OK: {} nodos -> {}'.format(total, args.out))
    print('  A={} ({:.1f}%)  B={}  C={}  | instrumented={} ({:.1f}%)'.format(
        pilas['A'], 100.0 * pilas['A'] / total, pilas['B'], pilas['C'],
        pilas['A'], 100.0 * pilas['A'] / total))
    print('  las 15 contractables son las 15 instrumented: todas se leen del '
          'codigo,\n  ninguna de un registro que llene una persona.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
