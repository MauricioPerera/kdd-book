#!/usr/bin/env python3
"""Construye books/codigo-limpio.json a partir del texto extraido del libro.

Los titulos de las heuristicas se leen del PDF extraido: no se escriben a mano.
La clasificacion (pila, instrumento, umbral) es el triaje, y va declarada aqui
de forma explicita para que sea auditable linea por linea.

**No se reproduce el texto del autor.** Cada nodo lleva el nombre de la
heuristica y su ubicacion (`capitulo 17, F1`) para que quien tenga el libro
pueda ir a leerla, pero el cuerpo del libro no se copia. Nada funcional depende
de esas citas: la propiedad medible vive en el instrumento, no en la prosa que
la describe.

Uso:
    python build_codigo_limpio.py <clean_code_es.txt> [-o books/codigo-limpio.json]
"""

import argparse
import json
import os
import re
import sys
import unicodedata


# ---------------------------------------------------------------------------
# Triaje: id -> (pila, instrumento, umbral)
# Pila A = existe una medicion determinista sobre el artefacto del que trata la
# tecnica, cuyo umbral ES la tecnica. Las 32 de Codigo Limpio son instrumented:
# el instrumento lee el codigo, no un registro que llene una persona.
# ---------------------------------------------------------------------------

A_NODES = {
    'C5': ('linter: regla ERA (codigo comentado)', 'comentarios_con_codigo: 0'),
    'E1': ('un solo comando de build; exit code', 'pasos_build_max: 1'),
    'E2': ('test_command; exit code', 'pasos_test_max: 1'),
    'F1': ('measure_complexity.params', 'params_max: 3'),
    'F2': ('AST: parametro mutado en el cuerpo', 'args_de_salida: 0'),
    'F3': ('AST: parametro booleano usado en condicional', 'args_indicador: 0'),
    'F4': ('analisis de alcanzabilidad (vulture/ruff)', 'funciones_muertas: 0'),
    'G3': ('mutation_audit sobre mutantes de limite', 'mutantes_limite_vivos: 0'),
    'G4': ('grep de supresiones (noqa, SuppressWarnings, skip)', 'supresiones: 0'),
    'G5': ('deteccion de clones (jscpd/CPD)', 'bloques_duplicados: 0'),
    'G7': ('grafo de referencias: la base nombra a su variante', 'refs_base_a_variante: 0'),
    'G8': ('conteo de miembros publicos por clase o modulo', 'api_publica_max'),
    'G9': ('linter: codigo inalcanzable', 'codigo_muerto: 0'),
    'G10': ('AST: distancia en lineas entre declaracion y primer uso', 'distancia_declaracion_max'),
    'G12': ('linter: imports y variables sin usar, constructores vacios', 'desorden: 0'),
    'G14': ('AST: accesos a miembros ajenos vs propios por metodo', 'accesos_ajenos_max'),
    'G15': ('AST: parametro que selecciona comportamiento', 'args_selector: 0'),
    'G23': ('AST: cadenas if/else o switch sobre discriminante de tipo', 'switch_sobre_tipo: 0'),
    'G24': ('run_linter_gate', 'linter exit 0'),
    'G25': ('linter: literales numericos fuera de constante (PLR2004)', 'numeros_magicos: 0'),
    'G28': ('AST: operadores booleanos por condicional', 'operadores_por_condicion_max'),
    'G29': ('AST: condicionales negadas', 'condicionales_negadas_max'),
    'G33': ('AST: subexpresion de limite repetida', 'subexpr_limite_duplicada: 0'),
    'G36': ('AST: profundidad de cadena de llamadas', 'chain_depth_max: 1'),
    'J1': ('linter: imports con comodin y conteo de imports', 'imports_comodin: 0'),
    'J2': ('AST: interfaz solo-constantes implementada', 'herencia_de_constantes: 0'),
    'N5': ('AST: longitud de identificador vs lineas del ambito', 'len(nombre) >= f(lineas_ambito)'),
    'N6': ('linter: prefijos hungaros y codificaciones en identificadores', 'codificaciones: 0'),
    'T1': ('cobertura', 'cobertura_min'),
    'T2': ('presencia del gate de cobertura en CI', 'gate_cobertura: presente'),
    'T5': ('mutation_audit sobre mutantes de limite', 'mutantes_limite_vivos: 0'),
    'T9': ('wall time de la suite', 'test_seconds_max'),
}

# Pila C: afirmaciones interpretativas sobre diagnostico. No son tecnicas con
# artefacto, asi que no llegan siquiera a preguntarse si son medibles.
C_NODES = {'T4', 'T7', 'T8'}

# Por que no es contractable. Solo para los casos donde el propio autor da la
# razon: son los que marcan la frontera y los que hay que poder citar.
WHY_NOT = {
    'G19': ('el autor la describe como monotona y sin umbral (siempre conviene '
            'mas y es dificil excederse), y ademas exige nombres descriptivos, '
            'que es la mitad no medible'),
    'G30': ('el autor cuenta operaciones semanticas y nunca da un numero; '
            'longitud y ciclomatica son proxies, no la propiedad'),
    'N1': 'lo descriptivo de un nombre es correspondencia semantica con el cuerpo',
    'C2': 'detectar que un comentario quedo obsoleto exige entender el codigo que describe',
}

# Enlaces del grafo. Solo relaciones que el propio libro establece o que son la
# misma propiedad vista dos veces; no se inventan vecindades tematicas.
LINKS = {
    'F1': ['G30'], 'F3': ['G15'], 'F4': ['G9'], 'F2': ['F1'],
    'G3': ['T5'], 'G5': ['G33', 'G12'], 'G9': ['F4'], 'G15': ['F3'],
    'G19': ['G28', 'N1'], 'G23': ['G30'], 'G28': ['G19', 'G29'],
    'G30': ['F1', 'G34'], 'G33': ['G5'], 'G34': ['G30'], 'G36': ['G14'],
    'N1': ['N2', 'N4', 'N5'], 'N2': ['N1'], 'N4': ['N1'], 'N5': ['N1'],
    'N7': ['N1'], 'C2': ['C3'], 'C3': ['C2'], 'C5': ['G9'],
    'T1': ['T2'], 'T2': ['T1'], 'T5': ['G3'], 'T4': ['G4'],
    'T7': ['T8'], 'T8': ['T7'], 'E1': ['E2'], 'E2': ['E1'],
}

FAMILIES = {
    'C': 'comentarios', 'E': 'entorno', 'F': 'funciones',
    'G': 'generales', 'J': 'java', 'N': 'nombres', 'T': 'pruebas',
}

_HEAD_RE = re.compile(r'^\s*([CEFGJNT]\d{1,2})\s*[:.]\s*(.+)$', re.M)


def slugify(text, maxlen=60):
    """kebab-case ASCII, estable y sin colisiones por acentos."""
    norm = unicodedata.normalize('NFKD', text)
    ascii_text = ''.join(c for c in norm if not unicodedata.combining(c))
    ascii_text = ascii_text.lower()
    ascii_text = re.sub(r'[^a-z0-9]+', '-', ascii_text).strip('-')
    if len(ascii_text) > maxlen:
        ascii_text = ascii_text[:maxlen].rstrip('-')
    return ascii_text


def extract_catalogue(text):
    """Devuelve {codigo: (titulo, cuerpo)} del catalogo del capitulo 17.

    Cada codigo aparece dos veces: una con su desarrollo y otra en un listado
    tipo indice con el cuerpo vacio. Se elige la aparicion de cuerpo mas largo,
    que da igual el orden en que el libro ponga el indice.
    """
    matches = list(_HEAD_RE.finditer(text))
    by_code = {}
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else match.start() + 2500
        code = match.group(1)
        body = text[match.end():end]
        previous = by_code.get(code)
        if previous is None or len(body) > len(previous[1]):
            by_code[code] = (match.group(2).strip(), body)
    return by_code


def build(text):
    catalogue = extract_catalogue(text)
    missing = [c for c in list(A_NODES) + sorted(C_NODES) if c not in catalogue]
    if missing:
        raise SystemExit('ERROR: codigos no encontrados en el texto: {}'.format(missing))

    def sort_key(code):
        return (code[0], int(code[1:]))

    id_by_code = {}
    for code in sorted(catalogue, key=sort_key):
        title = catalogue[code][0]
        id_by_code[code] = '{}-{}'.format(code.lower(), slugify(title))

    nodes = []
    for code in sorted(catalogue, key=sort_key):
        title, _body = catalogue[code]
        family = FAMILIES[code[0]]

        if code in A_NODES:
            pile, verification = 'A', 'instrumented'
            instrument, threshold = A_NODES[code]
        elif code in C_NODES:
            pile, verification, instrument, threshold = 'C', 'none', None, None
        else:
            pile, verification, instrument, threshold = 'B', 'none', None, None

        tags = ['codigo-limpio', family, {'A': 'contractable',
                                          'B': 'no-especificable',
                                          'C': 'conocimiento'}[pile]]
        if pile == 'A':
            tags.append('instrumented')

        node = {
            'id': id_by_code[code],
            'title': '{}: {}'.format(code, title),
            'description': '{} (heuristica {} del catalogo del capitulo 17).'.format(
                title, code),
            'type': 'Concept',
            'tags': tags,
            'pile': pile,
            'verification': verification,
            'locator': 'capitulo 17, {}'.format(code),
            'links': [id_by_code[t] for t in LINKS.get(code, []) if t in id_by_code],
        }
        if instrument:
            node['instrument'] = instrument
        if threshold:
            node['threshold'] = threshold
        if code in WHY_NOT:
            node['why_not'] = WHY_NOT[code]
        nodes.append(node)

    return {
        'source': {
            'slug': 'codigo-limpio',
            'title': 'Codigo Limpio',
            'author': 'Robert C. Martin',
            'file': 'Codigo_Limpio__PDFDrive_.pdf',
            'pages': 561,
            'extracted_with': 'pymupdf',
            'tags': ['fuente', 'libro', 'codigo-limpio'],
            'corpus': ('Las 66 heuristicas enumeradas por el autor en el capitulo 17 '
                       '("Olores y heuristica"): C1-C5, E1-E2, F1-F4, G1-G36, J1-J3, '
                       'N1-N7, T1-T9.'),
        },
        'nodes': nodes,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('text', help='texto extraido del PDF (UTF-8)')
    parser.add_argument('-o', '--out', default=os.path.join('books', 'codigo-limpio.json'))
    args = parser.parse_args(argv)

    with open(args.text, 'r', encoding='utf-8') as fh:
        spec = build(fh.read())

    os.makedirs(os.path.dirname(args.out) or '.', exist_ok=True)
    with open(args.out, 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(spec, fh, ensure_ascii=False, indent=2, sort_keys=False)
        fh.write('\n')

    piles = {'A': 0, 'B': 0, 'C': 0}
    for node in spec['nodes']:
        piles[node['pile']] += 1
    total = len(spec['nodes'])
    print('OK: {} nodos -> {}'.format(total, args.out))
    print('  A={} ({:.1f}%)  B={}  C={}'.format(
        piles['A'], 100.0 * piles['A'] / total, piles['B'], piles['C']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
