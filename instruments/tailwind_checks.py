#!/usr/bin/env python3
"""Instrumentos para las tecnicas medibles de Tailwind CSS.

Diez reglas, y el artefacto es nuevo: HTML/JSX con clases y hojas CSS con
`@theme`. Ninguna de las doce familias existentes lo lee.

**No hay un parser de HTML ni de CSS real detras de esto.** Son expresiones
regulares sobre el texto, igual que `html_checks` antes de tener un arbol: se
buscan atributos `class`/`className` con comillas simples y una vez, y bloques
`@theme`/`:root` contando llaves a mano. Lo que cada regla NO alcanza a ver
esta dicho en su docstring, no escondido en el codigo.

**El mapa utilidad -> propiedad CSS es deliberadamente chico.** Tailwind tiene
cientos de utilidades; cubrir todas seria mantener una copia de su motor. El
mapa cubre solo las familias que las propias paginas fuente usan como ejemplo
—`display`, `position`, `text-align`, `flex-direction`, `justify-content`,
`align-items`, `overflow`, `float`— y se puede ampliar con `--propiedades`. Las
reglas 11 y 15 solo pueden opinar sobre las utilidades del mapa: una utilidad
fuera de el no se mide, no se aprueba.

**La regla 8 (utilidades removidas) es angosta a proposito.** La guia de
actualizacion tiene dos tablas: "removidas" y "renombradas". Solo se mide la
primera —`bg-opacity-*`, `flex-shrink-*`, `overflow-ellipsis`...—, que dejo de
existir en v4. La segunda —`shadow` ahora es `shadow-sm`— sigue siendo una
clase valida en v4, solo que con otra escala: escribir `shadow` no es un error,
es ambiguo entre "intencional" y "migracion sin terminar", y esta regla no
adivina intencion.

Exit codes (convencion KDD):
  0  la propiedad se cumple
  1  no se cumple
  2  no se pudo verificar

Uso:
    python tailwind_checks.py --rule instalacion <vite.config.ts>
    python tailwind_checks.py --rule utilidades-en-conflicto --proyecto . <index.html>
    python tailwind_checks.py --list
"""

__all__ = [
    'NoVerificable',
    'check_clases_dinamicas',
    'check_instalacion',
    'check_mobile_first',
    'check_modificador_important',
    'check_namespace_color',
    'check_preprocesadores',
    'check_referencia',
    'check_theme_variables',
    'check_utilidades_en_conflicto',
    'check_utilidades_removidas',
    'main',
]

import argparse
import json
import os
import re
import sys

# Sobre que mide esta familia: el proyecto entero (plantillas, CSS, config).
#
# Lo declara cada familia y no una lista en `memoria.py`: ver el docstring de
# `_artefacto_de` en memoria.py sobre por que ese dato vive aca.
ARTEFACTO = 'proyecto'

MARKUP_EXT = ('.html', '.htm', '.jsx', '.tsx', '.vue', '.svelte', '.astro', '.php', '.erb')
CSS_EXT = ('.css',)
EXCLUIDOS = ('node_modules', '.git', 'dist', 'build', '.next', 'out', '__pycache__')

BREAKPOINTS = ('sm', 'md', 'lg', 'xl', '2xl')

# Familias de utilidades cubiertas: las que las propias paginas fuente usan
# como ejemplo. Ampliable con --propiedades.
PROPIEDAD_BASE = {
    'block': 'display', 'inline-block': 'display', 'inline': 'display',
    'flex': 'display', 'inline-flex': 'display', 'table': 'display',
    'grid': 'display', 'inline-grid': 'display', 'contents': 'display',
    'hidden': 'display',
    'static': 'position', 'fixed': 'position', 'absolute': 'position',
    'relative': 'position', 'sticky': 'position',
    'text-left': 'text-align', 'text-center': 'text-align',
    'text-right': 'text-align', 'text-justify': 'text-align',
    'text-start': 'text-align', 'text-end': 'text-align',
    'flex-row': 'flex-direction', 'flex-row-reverse': 'flex-direction',
    'flex-col': 'flex-direction', 'flex-col-reverse': 'flex-direction',
    'justify-start': 'justify-content', 'justify-end': 'justify-content',
    'justify-center': 'justify-content', 'justify-between': 'justify-content',
    'justify-around': 'justify-content', 'justify-evenly': 'justify-content',
    'items-start': 'align-items', 'items-end': 'align-items',
    'items-center': 'align-items', 'items-baseline': 'align-items',
    'items-stretch': 'align-items',
    'overflow-auto': 'overflow', 'overflow-hidden': 'overflow',
    'overflow-visible': 'overflow', 'overflow-scroll': 'overflow',
    'float-left': 'float', 'float-right': 'float', 'float-none': 'float',
}

# Familias genuinamente removidas en v4 (no renombradas: removidas).
_REMOVIDAS = re.compile(
    r'^(?:(?:bg|text|border|divide|ring|placeholder)-opacity-\d+'
    r'|flex-(?:shrink|grow)-.+'
    r'|overflow-ellipsis'
    r'|decoration-(?:slice|clone))$')

_CLASE_ATTR = re.compile(r'\b(?:class|className)\s*=\s*(["\'])((?:(?!\1).)*)\1', re.S)
# JSX/TSX escriben `className={...}` con llaves, no comillas: un template
# literal ahi adentro (`` `bg-${x}-600` ``) no lo ve `_CLASE_ATTR` porque no
# empieza con comilla. Es el patron mas comun de nombre de clase dinamico en
# React, y sin este segundo patron `clases-dinamicas` no lo veria nunca.
_CLASE_ATTR_JSX = re.compile(r'className\s*=\s*\{\s*`([^`]*)`\s*\}', re.S)
_DINAMICA = re.compile(r'\{\{|\$\{|#\{')

_COLOR_VALOR = re.compile(r'^(?:oklch|rgba?|hsla?)\(|^#[0-9a-fA-F]{3,8}\b')
_NAMESPACES_TEMA = ('color', 'font', 'text', 'spacing', 'radius', 'shadow',
                    'breakpoint', 'ease', 'animate', 'tracking', 'leading',
                    'inset', 'ring', 'blur', 'perspective', 'aspect')


class NoVerificable(Exception):
    """Falta el dato sin el cual la regla no se puede evaluar (exit 2)."""


def _archivos(proyecto, extensiones):
    """Rutas del proyecto con alguna de las extensiones dadas, sin vendor ni build."""
    out = []
    for raiz, dirs, nombres in os.walk(proyecto):
        dirs[:] = [d for d in dirs if d not in EXCLUIDOS]
        for nombre in sorted(nombres):
            if nombre.lower().endswith(extensiones):
                out.append(os.path.join(raiz, nombre))
    return out


def _leer(ruta):
    try:
        with open(ruta, 'r', encoding='utf-8') as fh:
            return fh.read()
    except (OSError, UnicodeDecodeError):
        return ''


def _clases_de(texto):
    """(linea, tokens) de cada atributo class/className NO dinamico.

    Los atributos con `{{`, `${` o `#{` los mide `clases-dinamicas` y no este
    helper: mezclar los dos daria tokens rotos donde antes habia una
    interpolacion.
    """
    out = []
    for m in _CLASE_ATTR.finditer(texto):
        contenido = m.group(2)
        if _DINAMICA.search(contenido):
            continue
        linea = texto.count('\n', 0, m.start()) + 1
        out.append((linea, contenido.split()))
    return out


def _propiedad_de(token, propiedades):
    """(propiedad, es_breakpoint, prefijos) del token, o None si no esta en el mapa."""
    partes = token.split(':')
    base = partes[-1]
    propiedad = propiedades.get(base)
    if propiedad is None:
        return None
    prefijos = partes[:-1]
    return propiedad, any(p in BREAKPOINTS for p in prefijos), prefijos


def _proyecto_de(opts, target):
    if opts.proyecto:
        return os.path.abspath(opts.proyecto)
    return os.path.dirname(os.path.abspath(target))


def _propiedades(opts):
    base = dict(PROPIEDAD_BASE)
    if opts.propiedades:
        if not os.path.isfile(opts.propiedades):
            raise NoVerificable('el mapa de propiedades declarado no existe: {}'
                                .format(opts.propiedades))
        try:
            with open(opts.propiedades, 'r', encoding='utf-8') as fh:
                base.update(json.load(fh))
        except ValueError as exc:
            raise NoVerificable('mapa de propiedades ilegible: {}'.format(exc))
    return base


# ---------------------------------------------------------------------------
# Getting started
# ---------------------------------------------------------------------------

def check_instalacion(proyecto, opts):
    """Installation: el punto de entrada de Vite declara el plugin y el import.

    Solo mide proyectos que usan Vite. Si no hay ningun `vite.config.*`, la
    tecnica que esta pagina documenta no aplica —Tailwind tambien se instala
    via PostCSS o su CLI— y no hay nada que verificar.
    """
    configs = [f for f in _archivos(proyecto, ('.ts', '.js', '.mjs', '.cjs'))
              if os.path.basename(f).startswith('vite.config.')]
    if not configs:
        raise NoVerificable('no hay vite.config.*: esta regla mide la instalacion '
                            'via el plugin de Vite, no otros bundlers')

    plugin = any('@tailwindcss/vite' in _leer(f) for f in configs)
    css_con_import = any('@import' in _leer(f) and 'tailwindcss' in _leer(f)
                         for f in _archivos(proyecto, CSS_EXT))

    out = []
    if not plugin:
        out.append((configs[0], 0, 'ningun vite.config declara el plugin '
                                   '@tailwindcss/vite'))
    if not css_con_import:
        out.append(('(css)', 0, 'ninguna hoja de estilos tiene '
                                '@import "tailwindcss";'))
    return out


def check_preprocesadores(proyecto, opts):
    """Compatibility: cero dependencias de Sass, Less o Stylus junto con v4.

    "Tailwind CSS v4.0 no esta disenado para usarse con preprocesadores CSS
    como Sass, Less o Stylus" — cita literal de la guia. Si el proyecto ni
    siquiera declara tailwindcss como dependencia, la regla no aplica.
    """
    manifiesto = os.path.join(proyecto, 'package.json')
    if not os.path.isfile(manifiesto):
        raise NoVerificable('no hay package.json: no se puede saber que '
                            'dependencias declara el proyecto')
    try:
        with open(manifiesto, 'r', encoding='utf-8') as fh:
            datos = json.load(fh)
    except ValueError as exc:
        raise NoVerificable('package.json ilegible: {}'.format(exc))

    deps = dict(datos.get('dependencies', {}))
    deps.update(datos.get('devDependencies', {}))
    if 'tailwindcss' not in deps:
        raise NoVerificable('el proyecto no declara tailwindcss como '
                            'dependencia: la regla no aplica')

    out = []
    for nombre, extension in (('sass', '.scss'), ('less', '.less'), ('stylus', '.styl')):
        if nombre in deps or 'node-' + nombre in deps:
            out.append(('package.json', 0, 'declara {} junto con tailwindcss'
                        .format(nombre)))
        elif _archivos(proyecto, (extension,)):
            out.append(('(archivos)', 0, 'hay archivos {} junto con tailwindcss'
                        .format(extension)))
    return out


def check_referencia(proyecto, opts):
    """Compatibility: los <style> de Vue/Svelte con @apply o @variant declaran @reference.

    Sin ese import, `@apply`/`@variant` no tienen de donde tomar el tema y el
    build falla o produce CSS vacio.
    """
    archivos = _archivos(proyecto, ('.vue', '.svelte'))
    if not archivos:
        raise NoVerificable('no hay componentes .vue/.svelte: la regla mide '
                            'bloques <style> de ese tipo de archivo')

    out = []
    for ruta in archivos:
        texto = _leer(ruta)
        for m in re.finditer(r'<style\b[^>]*>(.*?)</style>', texto, re.S | re.I):
            bloque = m.group(1)
            if re.search(r'@(?:apply|variant)\b', bloque) and '@reference' not in bloque:
                linea = texto.count('\n', 0, m.start()) + 1
                out.append((ruta, linea, '<style> usa @apply o @variant sin '
                                        '@reference'))
    return out


# ---------------------------------------------------------------------------
# Upgrade guide
# ---------------------------------------------------------------------------

def check_utilidades_removidas(proyecto, opts):
    """Upgrade guide: cero utilidades v3 removidas en las plantillas.

    Solo las que la guia llama "Removed Deprecated Utilities" —dejaron de
    existir—. Las "Renamed" (`shadow` -> `shadow-sm`) siguen siendo clases
    validas en v4 con otra escala: escribirlas no es un error, es ambiguo con
    una migracion sin terminar, y esta regla no adivina intencion.
    """
    archivos = _archivos(proyecto, MARKUP_EXT)
    if not archivos:
        raise NoVerificable('no hay archivos de plantillas para revisar')

    out = []
    for ruta in archivos:
        texto = _leer(ruta)
        for linea, tokens in _clases_de(texto):
            for token in tokens:
                if _REMOVIDAS.match(token):
                    out.append((ruta, linea, 'utilidad removida en v4: {!r}'
                                .format(token)))
    return out


def check_modificador_important(proyecto, opts):
    """Upgrade guide: el modificador important va como sufijo, no como prefijo.

    v3 escribia `!flex`; v4 escribe `flex!`. Marca cualquier token que empiece
    con `!`, incluidos los que llevan variantes: `!hover:bg-red-500`.
    """
    archivos = _archivos(proyecto, MARKUP_EXT)
    if not archivos:
        raise NoVerificable('no hay archivos de plantillas para revisar')

    out = []
    for ruta in archivos:
        texto = _leer(ruta)
        for linea, tokens in _clases_de(texto):
            for token in tokens:
                if token.startswith('!') and len(token) > 1:
                    out.append((ruta, linea, '{!r}: el modificador important va '
                                             'al final, no al principio'.format(token)))
    return out


# ---------------------------------------------------------------------------
# Core concepts
# ---------------------------------------------------------------------------

def check_utilidades_en_conflicto(proyecto, opts):
    """Styling with utility classes: cero utilidades en conflicto sobre la misma propiedad.

    Dos utilidades sin variante que fijan la misma propiedad CSS no "se
    combinan": gana la que queda mas tarde en la hoja generada, no la que esta
    mas a la derecha en `class=""`. Solo mira tokens sin prefijo de variante,
    y solo los que estan en el mapa de propiedades: fuera de el, no se mide.
    """
    archivos = _archivos(proyecto, MARKUP_EXT)
    if not archivos:
        raise NoVerificable('no hay archivos de plantillas para revisar')

    propiedades = _propiedades(opts)
    out = []
    for ruta in archivos:
        texto = _leer(ruta)
        for linea, tokens in _clases_de(texto):
            por_propiedad = {}
            for token in tokens:
                if ':' in token:
                    continue
                propiedad = propiedades.get(token)
                if propiedad:
                    por_propiedad.setdefault(propiedad, []).append(token)
            for propiedad, vistos in por_propiedad.items():
                if len(vistos) > 1:
                    out.append((ruta, linea, '{} en conflicto sobre {!r}: gana la '
                                             'que queda mas tarde en la hoja, no '
                                             'la de la derecha'
                                .format(', '.join(repr(v) for v in vistos), propiedad)))
    return out


def check_mobile_first(proyecto, opts):
    """Responsive design: la utilidad "mobile" va sin prefijo, no bajo sm:.

    El error que la guia marca: `sm:text-center` solo, sin una version sin
    prefijo, deja el elemento sin estilo de esa propiedad por debajo de 640px.
    Solo mide propiedades del mapa declarado.
    """
    archivos = _archivos(proyecto, MARKUP_EXT)
    if not archivos:
        raise NoVerificable('no hay archivos de plantillas para revisar')

    propiedades = _propiedades(opts)
    out = []
    for ruta in archivos:
        texto = _leer(ruta)
        for linea, tokens in _clases_de(texto):
            por_propiedad = {}
            for token in tokens:
                resuelto = _propiedad_de(token, propiedades)
                if resuelto is None:
                    continue
                propiedad, es_breakpoint, _prefijos = resuelto
                por_propiedad.setdefault(propiedad, []).append((token, es_breakpoint))
            for propiedad, vistos in por_propiedad.items():
                if all(es_bp for _t, es_bp in vistos):
                    out.append((ruta, linea, '{}: {} solo declarada bajo un '
                                             'breakpoint, sin version sin prefijo'
                                .format(vistos[0][0], propiedad)))
    return out


def check_theme_variables(proyecto, opts):
    """Theme variables: los tokens se declaran con @theme, top-level.

    "Theme variables are also required to be defined top-level and not nested
    under other selectors or media queries" — cita literal. Tambien marca los
    que se declaran con `:root` en vez de `@theme`.
    """
    archivos = _archivos(proyecto, CSS_EXT)
    if not archivos:
        raise NoVerificable('no hay hojas de estilo para revisar')

    out = []
    for ruta in archivos:
        texto = _leer(ruta)
        profundidad = 0
        for m in re.finditer(r'[{}]|@theme\b|:root\b', texto):
            token = m.group(0)
            if token == '{':
                profundidad += 1
            elif token == '}':
                profundidad = max(0, profundidad - 1)
            elif token == '@theme' and profundidad > 0:
                linea = texto.count('\n', 0, m.start()) + 1
                out.append((ruta, linea, '@theme anidado dentro de otro bloque'))
            elif token == ':root':
                bloque_m = re.search(r':root\s*\{([^}]*)\}', texto[m.start():], re.S)
                if bloque_m and re.search(
                        r'--(?:{})-'.format('|'.join(_NAMESPACES_TEMA)), bloque_m.group(1)):
                    linea = texto.count('\n', 0, m.start()) + 1
                    out.append((ruta, linea, 'variables de tema declaradas con '
                                             ':root en vez de @theme'))
    return out


def check_namespace_color(proyecto, opts):
    """Colors: los colores custom usan el namespace --color-*.

    Se detecta por la FORMA del valor —`oklch(...)`, `rgb(...)`, `#rrggbb`—,
    no por el nombre de la variable: si el valor es un color y el nombre no
    empieza con `--color-`, esta mal ubicado.
    """
    archivos = _archivos(proyecto, CSS_EXT)
    if not archivos:
        raise NoVerificable('no hay hojas de estilo para revisar')

    out = []
    declaracion = re.compile(r'(--[\w-]+)\s*:\s*([^;]+);')
    encontro_alguna = False
    for ruta in archivos:
        texto = _leer(ruta)
        for m in declaracion.finditer(texto):
            nombre, valor = m.group(1), m.group(2).strip()
            if not _COLOR_VALOR.match(valor):
                continue
            encontro_alguna = True
            if not nombre.startswith('--color-'):
                linea = texto.count('\n', 0, m.start()) + 1
                out.append((ruta, linea, '{} parece un color y no esta en el '
                                         'namespace --color-*'.format(nombre)))
    if not encontro_alguna and not out:
        raise NoVerificable('no se encontro ninguna variable con forma de '
                            'color: no hay nada que revisar')
    return out


def check_clases_dinamicas(proyecto, opts):
    """Detecting classes in source files: nunca construir el nombre de clase por concatenacion.

    "Tailwind treats files as plain text and cannot understand string
    concatenation or interpolation" — cita literal. Marca `{{ }}`, `${ }` o
    `#{ }` adentro de un atributo class/className.
    """
    archivos = _archivos(proyecto, MARKUP_EXT)
    if not archivos:
        raise NoVerificable('no hay archivos de plantillas para revisar')

    out = []
    for ruta in archivos:
        texto = _leer(ruta)
        for patron in (_CLASE_ATTR, _CLASE_ATTR_JSX):
            for m in patron.finditer(texto):
                contenido = m.group(2) if patron is _CLASE_ATTR else m.group(1)
                if _DINAMICA.search(contenido):
                    linea = texto.count('\n', 0, m.start()) + 1
                    out.append((ruta, linea, 'nombre de clase construido por '
                                             'interpolacion: {!r}'.format(contenido)))
    return out


RULES = {
    'clases-dinamicas': (check_clases_dinamicas, 'Deteccion de clases: nada de nombres construidos'),
    'instalacion': (check_instalacion, 'Installation: plugin e import declarados'),
    'mobile-first': (check_mobile_first, 'Responsive design: version sin prefijo para mobile'),
    'modificador-important': (check_modificador_important, 'Important: sufijo, no prefijo'),
    'namespace-color': (check_namespace_color, 'Colors: namespace --color-*'),
    'preprocesadores': (check_preprocesadores, 'Compatibility: cero Sass/Less/Stylus con v4'),
    'referencia': (check_referencia, 'Compatibility: @apply/@variant piden @reference'),
    'theme-variables': (check_theme_variables, 'Theme variables: @theme, top-level'),
    'utilidades-en-conflicto': (check_utilidades_en_conflicto, 'Cero utilidades en conflicto por propiedad'),
    'utilidades-removidas': (check_utilidades_removidas, 'Upgrade guide: cero utilidades removidas'),
}


def main(argv=None):
    """Corre la regla pedida sobre el proyecto dado y devuelve el exit code."""
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--rule')
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--proyecto', help='raiz del proyecto (por defecto, la del target)')
    parser.add_argument('--propiedades', help='JSON que amplia el mapa utilidad -> propiedad')
    parser.add_argument('target', nargs='?')
    args = parser.parse_args(argv)

    if args.list:
        for nombre in sorted(RULES):
            print('{:24} {}'.format(nombre, RULES[nombre][1]))
        return 0

    if args.rule not in RULES:
        print('NO-VERIFICABLE: regla desconocida: {!r} (ver --list)'.format(args.rule))
        return 2
    if not args.target and not args.proyecto:
        print('NO-VERIFICABLE: falta el punto de entrada del proyecto')
        return 2

    proyecto = _proyecto_de(args, args.target or '.')
    if not os.path.isdir(proyecto):
        print('NO-VERIFICABLE: no existe el proyecto {}'.format(proyecto))
        return 2

    func, etiqueta = RULES[args.rule]
    try:
        violaciones = func(proyecto, args)
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
