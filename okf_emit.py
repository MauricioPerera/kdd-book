#!/usr/bin/env python3
"""Emisor determinista de grafos OKF a partir de un libro triado.

Toma un JSON de nodos clasificados (la salida del triaje) y escribe un arbol
knowledge/ que pasa scripts/validate_okf.py del repo KDD sin intervencion
manual. Sin LLM, sin red, sin subprocess: solo stdlib.

El paso que este emisor existe para resolver es el cableado del grafo. Emitir
nodos sueltos es facil; lo que rompe la validacion es §5 (huerfanos) y §4
(enlaces rotos). Por eso:

  - la carpeta del libro se enlaza desde index.md, lo que hace alcanzables a
    todos sus .md hijos directos (§5);
  - todo enlace declarado en `links` se resuelve ANTES de escribir nada, y si
    alguno no existe el emisor aborta sin tocar el disco (§4).

Exit codes (convencion KDD):
  0  grafo emitido
  1  error: enlace no resoluble, id duplicado, campo invalido
  2  no se pudo verificar: JSON ilegible, destino no escribible

Uso:
    python okf_emit.py <nodos.json> [--out knowledge] [--dry-run]
"""

__all__ = ['EmitError', 'emit', 'main']

import argparse
import json
import os
import re
import sys


VALID_TYPES = {'Task Contract', 'Data Model', 'Architecture', 'Concept'}
VALID_PILES = {'A', 'B', 'C'}
VALID_VERIFICATION = {'instrumented', 'proxy', 'human_rubric', 'none'}

SOURCE_NODE = 'fuente.md'
INDEX_NAME = 'index.md'

# Marcadores del bloque que gestiona el emisor dentro de index.md. Hay un
# bloque POR LIBRO: con un solo bloque compartido, emitir un segundo libro
# reemplazaba la entrada del primero y sus nodos quedaban huerfanos en masa.
# Todo lo que se escriba fuera de estos marcadores se conserva intacto.
INDEX_BEGIN = '<!-- okf-emit:libro:{} -->'
INDEX_END = '<!-- /okf-emit:libro:{} -->'

_SLUG_RE = re.compile(r'^[a-z0-9][a-z0-9-]*$')


class EmitError(Exception):
    """Error de contenido: el JSON describe un grafo invalido (exit 1)."""


def _q(value):
    """Escalar YAML citado, en el dialecto que parsea validate_okf.py.

    El parser toma value[1:-1] cuando el primer y ultimo caracter son la misma
    comilla, sin interpretar escapes. Se normalizan las comillas simples
    internas a tipograficas para que el valor nunca termine antes de tiempo.
    """
    text = str(value).replace('\n', ' ').strip()
    text = text.replace("'", '’')
    return "'{}'".format(text)


def _tags(tags):
    return '[' + ', '.join(_q(t) for t in tags) + ']'


def _check_node(node, seen):
    """Valida un nodo del JSON. Lanza EmitError con el motivo exacto."""
    node_id = node.get('id', '')
    if not _SLUG_RE.match(str(node_id)):
        raise EmitError(
            "id invalido: {!r} (debe ser kebab-case en minusculas)".format(node_id))
    if node_id in seen:
        raise EmitError("id duplicado: {!r}".format(node_id))

    for key in ('title', 'description', 'type', 'tags'):
        if not node.get(key):
            raise EmitError("{}: campo requerido ausente o vacio: {}".format(node_id, key))

    if node['type'] not in VALID_TYPES:
        raise EmitError("{}: type invalido: {!r} (validos: {})".format(
            node_id, node['type'], sorted(VALID_TYPES)))

    tags = node['tags']
    if not isinstance(tags, list) or not tags:
        raise EmitError("{}: tags debe ser una lista no vacia".format(node_id))
    for tag in tags:
        if not isinstance(tag, str) or not tag:
            raise EmitError("{}: tag vacio o no string: {!r}".format(node_id, tag))
        if tag != tag.lower():
            raise EmitError("{}: tag con mayusculas: {!r}".format(node_id, tag))

    pile = node.get('pile')
    if pile is not None and pile not in VALID_PILES:
        raise EmitError("{}: pile invalido: {!r} (validos: {})".format(
            node_id, pile, sorted(VALID_PILES)))

    verification = node.get('verification')
    if verification is not None and verification not in VALID_VERIFICATION:
        raise EmitError("{}: verification invalido: {!r} (validos: {})".format(
            node_id, verification, sorted(VALID_VERIFICATION)))

    # Una tecnica contractable sin instrumento declarado es justo el error que
    # este pipeline existe para no cometer: promete verificacion que no tiene.
    if pile == 'A' and not node.get('instrument'):
        raise EmitError(
            "{}: pila A sin 'instrument' declarado (una tecnica contractable "
            "debe nombrar el instrumento que la mide)".format(node_id))
    if pile == 'A' and verification in (None, 'none'):
        raise EmitError(
            "{}: pila A sin 'verification' (declara instrumented o proxy)".format(node_id))


def _link_href(target, slug):
    """Ruta relativa del enlace desde un nodo del libro `slug`.

    Un destino puede ser `id` (nodo del mismo libro) o `otro-libro/id` (nodo de
    otro libro ya emitido). Los enlaces entre libros son el punto del grafo: la
    misma tecnica operacionalizada por un autor y no por otro solo se puede
    decir si los nodos se pueden citar entre si.
    """
    if '/' in target:
        return '../{}.md'.format(target)
    del slug
    return '{}.md'.format(target)


def _resolve_links(nodes, out_dir, slug):
    """§4: todo destino de `links` debe existir antes de escribir nada.

    Dentro del libro se comprueba contra los ids del propio spec. Hacia otro
    libro se comprueba contra el disco: el otro libro tiene que estar emitido,
    y si no lo esta el emisor lo dice en vez de dejar un enlace roto.
    """
    ids = {n['id'] for n in nodes}
    ids.add('fuente')
    broken = []
    for node in nodes:
        for target in node.get('links', []):
            if '/' in target:
                otro = os.path.join(out_dir, *target.split('/')) + '.md'
                if not os.path.isfile(otro):
                    broken.append((node['id'], target + ' (otro libro, no emitido)'))
            elif target not in ids:
                broken.append((node['id'], target))
    if broken:
        detail = '; '.join('{} -> {}'.format(src, dst) for src, dst in sorted(broken))
        raise EmitError(
            "enlaces no resolubles ({}): {}".format(len(broken), detail))
    return ids


def _render_node(node, source):
    """Devuelve el markdown completo de un nodo OKF."""
    out = []
    out.append('---')
    out.append('type: {}'.format(_q(node['type'])))
    out.append('title: {}'.format(_q(node['title'])))
    out.append('description: {}'.format(_q(node['description'])))
    out.append('tags: {}'.format(_tags(node['tags'])))
    out.append('---')
    out.append('')
    out.append('# {}'.format(node['title']))
    out.append('')

    if node.get('body'):
        out.append(node['body'].strip())
        out.append('')

    if node.get('alias'):
        out.append('Tambien conocida como: {}.'.format(
            ', '.join(node['alias'])))
        out.append('')

    if node.get('defining_property'):
        out.append('## Propiedad definitoria')
        out.append('')
        out.append(node['defining_property'].strip())
        out.append('')

    pile = node.get('pile')
    if pile:
        out.append('## Verificabilidad')
        out.append('')
        label = {
            'A': 'A - contractable',
            'B': 'B - tecnica real, sin propiedad definitoria medible',
            'C': 'C - conocimiento',
        }[pile]
        out.append('- Pila: {}'.format(label))
        if node.get('verification'):
            out.append('- verification_type: `{}`'.format(node['verification']))
        if node.get('instrument'):
            out.append('- Instrumento: `{}`'.format(node['instrument']))
        if node.get('threshold'):
            out.append('- Umbral: `{}`'.format(node['threshold']))
        if pile == 'B' and node.get('why_not'):
            out.append('- No contractable porque: {}'.format(node['why_not']))
        out.append('')

    # La cita es opcional a proposito: un grafo derivado de un libro con
    # derechos puede referenciar donde esta la tecnica sin reproducir su texto.
    # Nada funcional depende de la cita — la propiedad medible vive en el
    # instrumento, no en la prosa que la describe.
    locator = node.get('locator')
    if node.get('quote') or locator:
        out.append('## En el libro')
        out.append('')
        if node.get('quote'):
            out.append('> {}'.format(node['quote'].strip()))
            out.append('')
        suffix = ' ({})'.format(locator) if locator else ''
        out.append('-- [{}]({}){}'.format(source['title'], SOURCE_NODE, suffix))
        out.append('')

    links = node.get('links', [])
    if links:
        out.append('## Relacionados')
        out.append('')
        for target in links:
            etiqueta = target.split('/')[-1]
            sufijo = ' (en {})'.format(target.split('/')[0]) if '/' in target else ''
            out.append('- [{}]({}){}'.format(
                etiqueta, _link_href(target, source['slug']), sufijo))
        out.append('')

    return '\n'.join(out).rstrip() + '\n'


def _render_source(source, nodes):
    """Nodo de procedencia: de donde salio el grafo y como se midio."""
    counts = {'A': 0, 'B': 0, 'C': 0}
    instrumented = 0
    for node in nodes:
        pile = node.get('pile')
        if pile in counts:
            counts[pile] += 1
        if node.get('verification') == 'instrumented':
            instrumented += 1
    total = len(nodes)

    def pct(value):
        """Un porcentaje sobre el total, o "n/d" si no hay nada que dividir."""
        return '{:.1f}%'.format(100.0 * value / total) if total else 'n/d'

    out = []
    out.append('---')
    out.append("type: 'Concept'")
    out.append('title: {}'.format(_q('Fuente: ' + source['title'])))
    out.append('description: {}'.format(_q(
        'Procedencia y medicion de contractabilidad del grafo derivado de este libro.')))
    out.append('tags: {}'.format(_tags(source.get('tags', ['fuente', 'libro']))))
    out.append('---')
    out.append('')
    out.append('# Fuente: {}'.format(source['title']))
    out.append('')
    for label, key in (('Autor', 'author'), ('Archivo', 'file'),
                       ('Paginas', 'pages'), ('Extraido con', 'extracted_with'),
                       ('sha256', 'sha256')):
        if source.get(key):
            out.append('- {}: {}'.format(label, source[key]))
    out.append('')
    out.append('## Corpus')
    out.append('')
    out.append(source.get('corpus', 'n/d'))
    out.append('')
    out.append('El corpus es una lista cerrada del autor. Eso es deliberado: si el')
    out.append('pipeline eligiera que cuenta como tecnica, la fraccion medida seria')
    out.append('una seleccion y no una medicion.')
    out.append('')
    out.append('## Medicion')
    out.append('')
    out.append('| Pila | n | % |')
    out.append('|---|---|---|')
    out.append('| A - contractable | {} | {} |'.format(counts['A'], pct(counts['A'])))
    out.append('| B - no especificable | {} | {} |'.format(counts['B'], pct(counts['B'])))
    out.append('| C - conocimiento | {} | {} |'.format(counts['C'], pct(counts['C'])))
    out.append('')
    out.append('**instrumented: {}/{} = {}**'.format(instrumented, total, pct(instrumented)))
    out.append('')
    out.append('La fraccion que decide el ruteo es `instrumented`, no la contractable:')
    out.append('mide si el instrumento lee el artefacto del que trata la tecnica, o')
    out.append('un registro que llena una persona.')
    out.append('')

    # Indice de titulos. El id de un nodo es el identificador del autor y nada
    # mas (`g36`, `142`, `08`) para que sea estable entre idiomas; el titulo es
    # una etiqueta que cambia con la edicion. Este listado es donde se recupera
    # la navegabilidad que el id ya no da.
    out.append('## Indice')
    out.append('')
    out.append('El id de cada nodo es el identificador del autor, no un resumen del')
    out.append('titulo: asi el mismo nodo tiene el mismo id en cualquier edicion o')
    out.append('traduccion, y los enlaces entre libros siguen resolviendo. El titulo')
    out.append('cambia con la edicion; el id no.')
    out.append('')
    out.append('| id | tecnica | pila |')
    out.append('|---|---|---|')
    for node in nodes:
        out.append('| [{}]({}.md) | {} | {} |'.format(
            node['id'], node['id'], node['title'], node.get('pile', '-')))
    out.append('')
    return '\n'.join(out).rstrip() + '\n'


def _render_index_block(source, nodes):
    """Bloque gestionado de UN libro dentro de index.md.

    Enlaza la carpeta, que es lo que satisface §5: los .md hijos directos de
    una carpeta enlazada quedan alcanzables.
    """
    slug = source['slug']
    out = []
    out.append(INDEX_BEGIN.format(slug))
    out.append('- [{}]({}/) - {} nodos derivados del libro. Procedencia y medicion en'
               ' [fuente]({}/{}).'.format(source['title'], slug, len(nodes) + 1,
                                          slug, SOURCE_NODE))
    out.append(INDEX_END.format(slug))
    return '\n'.join(out)


def _merge_index(existing, block, slug):
    """Inserta o reemplaza el bloque de ESTE libro, sin tocar el de los demas."""
    begin, end = INDEX_BEGIN.format(slug), INDEX_END.format(slug)
    if begin in existing and end in existing:
        head = existing.split(begin)[0]
        tail = existing.split(end, 1)[1]
        return head + block + tail
    base = existing.rstrip()
    if not base:
        base = '# Indice de conocimiento\n\n## Libros'
    return base + '\n\n' + block + '\n'


def emit(spec, out_dir, dry_run=False):
    """Escribe el grafo. Devuelve la lista de rutas relativas escritas."""
    source = spec['source']
    nodes = spec['nodes']

    slug = source.get('slug', '')
    if not _SLUG_RE.match(str(slug)):
        raise EmitError("source.slug invalido: {!r} (kebab-case en minusculas)".format(slug))

    seen = set()
    for node in nodes:
        _check_node(node, seen)
        seen.add(node['id'])

    # §4 antes de tocar el disco: un grafo a medias es peor que ninguno.
    _resolve_links(nodes, out_dir, slug)

    book_dir = os.path.join(out_dir, slug)
    index_path = os.path.join(out_dir, INDEX_NAME)

    existing_index = ''
    if os.path.isfile(index_path):
        with open(index_path, 'r', encoding='utf-8') as fh:
            existing_index = fh.read()
    new_index = _merge_index(existing_index,
                             _render_index_block(source, nodes), slug)

    files = {os.path.join(book_dir, SOURCE_NODE): _render_source(source, nodes)}
    for node in nodes:
        files[os.path.join(book_dir, node['id'] + '.md')] = _render_node(node, source)
    files[index_path] = new_index

    written = []
    if not dry_run:
        os.makedirs(book_dir, exist_ok=True)
        for path in sorted(files):
            with open(path, 'w', encoding='utf-8', newline='\n') as fh:
                fh.write(files[path])
    for path in sorted(files):
        written.append(os.path.relpath(path, out_dir).replace(os.sep, '/'))
    return written


def main(argv=None):
    """Emite el grafo OKF de una fuente y devuelve el exit code."""
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('spec', help='JSON de nodos triados')
    parser.add_argument('--out', default='knowledge', help='directorio knowledge/ destino')
    parser.add_argument('--dry-run', action='store_true',
                        help='valida y lista lo que escribiria, sin tocar el disco')
    args = parser.parse_args(argv)

    try:
        with open(args.spec, 'r', encoding='utf-8') as fh:
            spec = json.load(fh)
    except (OSError, ValueError) as exc:
        print('NO-VERIFICABLE: no se pudo leer el spec: {}'.format(exc))
        return 2

    try:
        written = emit(spec, args.out, dry_run=args.dry_run)
    except EmitError as exc:
        print('ERROR: {}'.format(exc))
        return 1
    except OSError as exc:
        print('NO-VERIFICABLE: no se pudo escribir en {}: {}'.format(args.out, exc))
        return 2

    verb = 'se escribiria' if args.dry_run else 'escrito'
    print('OK: {} archivo(s) {} en {}'.format(len(written), verb, args.out))
    for path in written:
        print('  {}'.format(path))
    return 0


if __name__ == '__main__':
    sys.exit(main())
