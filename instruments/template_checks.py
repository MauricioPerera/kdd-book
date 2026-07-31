#!/usr/bin/env python3
"""Instrumento que mide sobre plantillas (htmx, "Rule 1: Escape All User Content").

La ultima de las seis medibles de htmx, y la que quedo sin instrumento hasta
ahora por un motivo concreto: **el marcador de interpolacion sin escapar cambia
con cada motor**. En handlebars el escape se decide por interpolacion
(`{{x}}` escapa, `{{{x}}}` no); en jinja2 y django se decide en la aplicacion
—`autoescape`— y desde la plantilla ES INVISIBLE. Un instrumento que adivinara
el motor estaria inventando la convencion del proyecto.

Asi que el proyecto declara: `--motor`, y para los motores con estado global
tambien `--autoescape`. Es la misma forma que `arch_checks`, donde el proyecto
declara sus capas: cuando el dato que decide la medicion vive fuera del
artefacto, se pide, no se supone. Sin la declaracion, exit 2.

    escapado    toda interpolacion sale escapada

**Lo que esta regla NO mide.** Escapar para HTML no protege todos los
contextos: dentro de un `<script>`, en un atributo sin comillas o en un `href`
que termina siendo `javascript:`, el escape de HTML no alcanza. Eso es
escapado sensible al contexto y es otra tecnica; medirlo pediria saber en que
contexto cae cada interpolacion, o sea parsear el HTML que la plantilla todavia
no genero. Se dice aca para que el verde no se lea como mas de lo que es.

Exit codes (convencion KDD):
  0  toda interpolacion sale escapada
  1  hay al menos una sin escapar
  2  no se pudo verificar (falta la declaracion, o no hay interpolaciones)

Uso:
    python template_checks.py --rule escapado --motor jinja2 --autoescape on <t.html>
    python template_checks.py --rule escapado --motor handlebars <t.hbs>
    python template_checks.py --list
"""

import argparse
import os
import re
import sys

# Sobre que mide esta familia: una plantilla sin renderizar.
#
# Lo declara cada familia y no una lista en `memoria.py`, porque esa lista
# ya quedo vieja dos veces. `aplicar` elige por este campo que instrumentos
# puede correr sobre lo que le dieron; sin el, agregar una familia la deja
# afuera en silencio y nada falla.
ARTEFACTO = 'plantilla'


class NoVerificable(Exception):
    """Falta el dato sin el cual la regla no se puede evaluar (exit 2)."""


# Motores cuyo escape se decide en la aplicacion y no en la plantilla. Para
# estos hace falta `--autoescape`: la plantilla sola no lo dice.
GLOBAL = ('jinja2', 'django')

# Motores cuyo escape se decide en cada interpolacion, por sintaxis.
POR_INTERPOLACION = ('handlebars', 'mustache')

MOTORES = GLOBAL + POR_INTERPOLACION

COMENTARIO = {
    'jinja2': re.compile(r'\{#.*?#\}', re.S),
    'django': re.compile(r'\{#.*?#\}', re.S),
    'handlebars': re.compile(r'\{\{!--.*?--\}\}|\{\{!.*?\}\}', re.S),
    'mustache': re.compile(r'\{\{!.*?\}\}', re.S),
}

# La salida de escape de cada motor: lo que apaga el escapado a proposito.
CRUDO = {
    'jinja2': re.compile(r'\|\s*safe\b|\bMarkup\s*\('),
    'django': re.compile(r'\|\s*safe\b|\bmark_safe\s*\('),
}

# El escapado explicito, que salva la interpolacion aunque el global este off.
ESCAPA = {
    'jinja2': re.compile(r'\|\s*(?:e|escape|forceescape)\b'),
    'django': re.compile(r'\|\s*(?:escape|force_escape)\b'),
}

INTERPOLACION = re.compile(r'\{\{(.*?)\}\}', re.S)

# `{% autoescape true %}` / `{% endautoescape %}`, en las dos ortografias.
BLOQUE = re.compile(
    r'\{%-?\s*autoescape\s+(true|false|on|off)\s*-?%\}'
    r'|\{%-?\s*(endautoescape)\s*-?%\}', re.I)

# Handlebars y mustache: lo que no es una interpolacion de valor.
NO_ES_VALOR = '#/^>!'

# Una interpolacion cuyo contenido es una constante no trae contenido de
# usuario. Excluirla evita marcar en rojo `{{ "-" }}`, que no es lo que la
# tecnica pide arreglar.
LITERAL = re.compile(r'''^\s*(?:'[^']*'|"[^"]*"|\d+(?:\.\d+)?)\s*$''')


def _blanquear(texto, patron):
    """Borra lo que matchea dejando los saltos de linea en su lugar.

    Hay que preservarlos: los numeros de linea del reporte se calculan contando
    saltos, y borrar un comentario multilinea de cuajo correria todo lo de
    abajo.
    """
    def _reemplazo(m):
        return re.sub(r'[^\n]', ' ', m.group(0))
    return patron.sub(_reemplazo, texto)


def _linea(texto, pos):
    return texto.count('\n', 0, pos) + 1


def _estado(texto, inicial):
    """Cambios de estado del autoescape a lo largo del archivo.

    Devuelve [(posicion, activo)] ordenado. Se lleva una pila porque los
    bloques anidan y `{% endautoescape %}` tiene que devolver al estado de
    afuera, no al global.
    """
    pila = [inicial]
    cambios = [(0, inicial)]
    for m in BLOQUE.finditer(texto):
        if m.group(2):
            if len(pila) > 1:
                pila.pop()
        else:
            pila.append(m.group(1).lower() in ('true', 'on'))
        cambios.append((m.end(), pila[-1]))
    return cambios


def _activo_en(cambios, pos):
    activo = cambios[0][1]
    for desde, valor in cambios:
        if desde <= pos:
            activo = valor
        else:
            break
    return activo


def _analizar_global(texto, motor, autoescape):
    """jinja2 y django: estado global, con salidas y bloques que lo cambian."""
    limpio = _blanquear(texto, COMENTARIO[motor])
    cambios = _estado(limpio, autoescape)
    crudo, escapa = CRUDO[motor], ESCAPA[motor]

    total = 0
    hallazgos = []
    for m in INTERPOLACION.finditer(limpio):
        expresion = m.group(1)
        if LITERAL.match(expresion):
            continue
        total += 1
        if crudo.search(expresion):
            hallazgos.append((_linea(limpio, m.start()),
                              '{{{{{}}}}} usa la salida de escape del motor: '
                              'lo que venga del usuario entra crudo en el HTML'
                              .format(expresion.strip())))
        elif not escapa.search(expresion) and not _activo_en(cambios, m.start()):
            hallazgos.append((_linea(limpio, m.start()),
                              '{{{{{}}}}} se interpola con el autoescape apagado: '
                              'ni el motor ni un filtro la escapan'
                              .format(expresion.strip())))
    return total, hallazgos


def _analizar_por_interpolacion(texto, motor):
    """handlebars y mustache: el escape se lee en la sintaxis misma."""
    limpio = _blanquear(texto, COMENTARIO[motor])
    hallazgos = []
    total = 0

    for m in re.finditer(r'\{\{\{(.*?)\}\}\}', limpio, re.S):
        total += 1
        hallazgos.append((_linea(limpio, m.start()),
                          '{{{{{{{}}}}}}} es triple: el triple stache no escapa'
                          .format(m.group(1).strip())))
    # Se borran antes de buscar las simples: `{{{x}}}` contiene un `{{...}}`
    # y sin esto la misma interpolacion se contaria dos veces, una de ellas
    # como si estuviera bien.
    limpio = _blanquear(limpio, re.compile(r'\{\{\{.*?\}\}\}', re.S))

    for m in re.finditer(r'\{\{&(.*?)\}\}', limpio, re.S):
        total += 1
        hallazgos.append((_linea(limpio, m.start()),
                          '{{{{&{}}}}} usa el ampersand: no escapa'
                          .format(m.group(1).strip())))
    limpio = _blanquear(limpio, re.compile(r'\{\{&.*?\}\}', re.S))

    for m in INTERPOLACION.finditer(limpio):
        if m.group(1)[:1] in NO_ES_VALOR:  # secciones, cierres, parciales
            continue
        if LITERAL.match(m.group(1)):
            continue
        total += 1
    return total, hallazgos


def check_escapado(archivos, opts):
    """Toda interpolacion de la plantilla sale escapada.

    La regla 1 de seguridad de htmx dice exactamente esto, y es medible porque
    el autor la operacionalizo: no es "cuidado con el XSS" sino "escapa todo el
    contenido de usuario". El umbral es cero.
    """
    if not opts.motor:
        raise NoVerificable(
            'hay que declarar el motor con --motor ({}): el marcador de '
            'interpolacion sin escapar cambia con cada uno, y adivinarlo seria '
            'inventar la convencion del proyecto'.format(', '.join(MOTORES)))
    if opts.motor not in MOTORES:
        raise NoVerificable('motor desconocido: {!r} (conocidos: {})'
                            .format(opts.motor, ', '.join(MOTORES)))

    if opts.motor in GLOBAL:
        if opts.autoescape is None:
            raise NoVerificable(
                'con {} hay que declarar --autoescape on|off: el escapado se '
                'configura en la aplicacion y desde la plantilla es invisible, '
                'asi que sin el dato la misma plantilla es segura o no segun '
                'algo que este instrumento no ve'.format(opts.motor))
    elif opts.autoescape is not None:
        raise NoVerificable(
            'con {} no corresponde --autoescape: aca el escapado se decide en '
            'cada interpolacion por sintaxis, no hay estado global que '
            'declarar, y aceptarlo haria creer que la declaracion sirvio para '
            'algo'.format(opts.motor))

    total = 0
    out = []
    for ruta, texto in archivos:
        if opts.motor in GLOBAL:
            cuantas, hallazgos = _analizar_global(
                texto, opts.motor, opts.autoescape == 'on')
        else:
            cuantas, hallazgos = _analizar_por_interpolacion(texto, opts.motor)
        total += cuantas
        out.extend((ruta, linea, detalle) for linea, detalle in hallazgos)

    if not total:
        raise NoVerificable(
            'ninguno de los {} archivo(s) tiene interpolaciones: no hay '
            'contenido que escapar, y decir "verde" seria decir que se midio '
            'algo'.format(len(archivos)))
    return out


RULES = {
    'escapado': (check_escapado, 'Escapado: toda interpolacion sale escapada'),
}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--rule')
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--motor', help='motor de plantillas: {}'.format(
        ', '.join(MOTORES)))
    parser.add_argument('--autoescape', choices=('on', 'off'),
                        help='estado del autoescape en la aplicacion (jinja2, django)')
    parser.add_argument('--plantillas', action='append', default=[],
                        help='plantilla a medir, aparte de los posicionales')
    parser.add_argument('files', nargs='*')
    args = parser.parse_args(argv)

    if args.list:
        for nombre in sorted(RULES):
            print('{:11} {}'.format(nombre, RULES[nombre][1]))
        return 0

    if args.rule not in RULES:
        print('NO-VERIFICABLE: regla desconocida: {!r} (ver --list)'.format(args.rule))
        return 2

    # `--plantillas` separa lo que se edita de lo que se mide, igual que
    # `--proyecto` en arch_checks y `--capturas` en http_checks. Aca hace falta
    # porque el target del contrato puede ser la vista que arma el contexto
    # mientras la plantilla es otro archivo.
    rutas = list(args.plantillas) + list(args.files)
    if not rutas:
        print('NO-VERIFICABLE: no se indicaron plantillas')
        return 2

    func, etiqueta = RULES[args.rule]
    archivos = []
    for ruta in rutas:
        if not os.path.isfile(ruta):
            print('NO-VERIFICABLE: no existe {}'.format(ruta))
            return 2
        try:
            with open(ruta, 'r', encoding='utf-8') as fh:
                archivos.append((ruta, fh.read()))
        except (OSError, UnicodeDecodeError) as exc:
            print('NO-VERIFICABLE: {}: {}'.format(etiqueta, exc))
            return 2

    try:
        violaciones = func(archivos, args)
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
