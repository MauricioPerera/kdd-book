#!/usr/bin/env python3
"""Instrumentos para las tecnicas medibles de la guia de estilo de Google.

Cuarenta y dos reglas. La octava fuente entro para aislar una variable —el
genero del documento— y lo que quedo fue que la contractabilidad depende de
**la naturaleza de la propiedad**, no del genero ni de si el artefacto es
codigo o prosa. Esta familia es la prueba: lee texto (Markdown o cualquier
documento de prosa) y mide el mismo tipo de cosa que `pep8_checks` mide sobre
Python — forma tipografica y lexico — no significado.

**Lo que estas reglas NO pueden ver, dicho de entrada.** "Voz y tono",
"antropomorfismo", "audiencia global" quedaron en pila B porque piden juzgar
sentido, y estas 42 reglas leen forma y vocabulario. Ninguna decide si una
frase tiene sentido: cuentan comas, dos puntos, mayusculas, patrones de
caracteres.

Seis reglas dependen de un vocabulario que el proyecto declara —terminos
desaconsejados, nombres de producto, lenguaje inclusivo, jerga, tipos de
aviso— porque la guia da el mecanismo (una lista) y no la lista misma: cada
proyecto tiene la propia. Sin la declaracion, exit 2 — la misma forma que
`arch_checks` con las capas y `template_checks` con el motor.

Exit codes (convencion KDD):
  0  la propiedad se cumple
  1  no se cumple
  2  no se pudo verificar

Uso:
    python prosa_checks.py --rule coma-serial <documento.md>
    python prosa_checks.py --rule lista-palabras --lista palabras.json <doc.md>
    python prosa_checks.py --list
"""

__all__ = [
    'Documento',
    'NoVerificable',
    'check_abreviaturas_latinas',
    'check_alt_texto',
    'check_and_or',
    'check_anclas',
    'check_avisos_tipo',
    'check_bloques_codigo',
    'check_coma_serial',
    'check_comillas_puntuacion',
    'check_dominios',
    'check_encabezados_caja',
    'check_encabezados_unicos',
    'check_fechas',
    'check_html_en_markdown',
    'check_inclusivo',
    'check_items_lista',
    'check_jerga',
    'check_lista_palabras',
    'check_marcadores',
    'check_mayuscula_dos_puntos',
    'check_minimizadores',
    'check_nombres_archivo',
    'check_nombres_producto',
    'check_notacion_matematica',
    'check_notas_pie',
    'check_numeros_chicos',
    'check_parentesis_anidados',
    'check_plural_parentesis',
    'check_posesivo_producto',
    'check_primera_persona',
    'check_procedimientos',
    'check_pronombres_genero',
    'check_punto_final',
    'check_puntos_suspensivos',
    'check_raya',
    'check_sintaxis_cli',
    'check_tablas_encabezado',
    'check_telefonos',
    'check_tiempo_futuro',
    'check_tiempo_relativo',
    'check_texto_enlace',
    'check_unidades',
    'check_verbos_interaccion',
    'main',
]

import argparse
import json
import os
import re
import sys

# Sobre que mide esta familia: un documento de prosa (Markdown u otro texto).
#
# Lo declara cada familia y no una lista en `memoria.py`: ver el docstring de
# `_artefacto_de` en memoria.py sobre por que ese dato vive aca.
ARTEFACTO = 'prosa'


class NoVerificable(Exception):
    """Falta el dato sin el cual la regla no se puede evaluar (exit 2)."""


_FENCE = re.compile(r'```.*?```', re.S)
_INLINE_CODE = re.compile(r'`[^`\n]+`')
_HEADING = re.compile(r'^(#{1,6})\s+(.*?)\s*$', re.M)
_IMAGE = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
_LINK = re.compile(r'(?<!!)\[([^\]]*)\]\(([^)]+)\)')
_BARE_URL = re.compile(r'(?<![(\[])\bhttps?://\S+')


def _leer(ruta):
    try:
        with open(ruta, 'r', encoding='utf-8') as fh:
            return fh.read()
    except OSError as exc:
        raise NoVerificable('no se pudo leer {}: {}'.format(ruta, exc))
    except UnicodeDecodeError as exc:
        raise NoVerificable(
            'el archivo no decodifica como UTF-8: {}. Sin poder leerlo no se '
            'puede medir nada de su prosa'.format(exc))


def _mascarar(texto):
    """Blanquea bloques de codigo e inline code, preservando saltos de linea.

    Las reglas de prosa no miden sobre codigo: un identificador con guion
    bajo, un "e.g." dentro de un ejemplo, o un numero pegado a una letra en un
    nombre de variable no son violaciones de estilo de prosa.
    """
    def _blanco(m):
        return re.sub(r'[^\n]', ' ', m.group(0))
    return _INLINE_CODE.sub(_blanco, _FENCE.sub(_blanco, texto))


def _encabezados(texto):
    return [(texto.count('\n', 0, m.start()) + 1, len(m.group(1)), m.group(2))
            for m in _HEADING.finditer(texto)]


def _slug(titulo):
    """Un slug al estilo GitHub: minusculas, sin puntuacion, espacios a guion."""
    limpio = re.sub(r'[^\w\s-]', '', titulo.lower())
    return re.sub(r'\s+', '-', limpio.strip())


def _cargar_lista(ruta, opcion):
    """Carga el JSON declarado con `--<opcion>`, o exige que se declare.

    La guia da el mecanismo (una lista) y no la lista misma: cada proyecto
    tiene su propio vocabulario, y adivinarlo seria inventar la convencion.
    """
    if not ruta:
        raise NoVerificable(
            'hay que declarar {}: la guia da el mecanismo, el vocabulario es '
            'del proyecto'.format(opcion))
    if not os.path.isfile(ruta):
        raise NoVerificable('la lista declarada no existe: {}'.format(ruta))
    try:
        with open(ruta, 'r', encoding='utf-8') as fh:
            return json.load(fh)
    except ValueError as exc:
        raise NoVerificable('lista ilegible: {}'.format(exc))


def _buscar(prosa, terminos):
    """(linea, termino, coincidencia) de cada aparicion de cada termino."""
    out = []
    for termino in terminos:
        for m in re.finditer(r'\b{}\b'.format(re.escape(termino)), prosa, re.I):
            out.append((prosa.count('\n', 0, m.start()) + 1, termino, m.group(0)))
    return out


class Documento:
    """Un documento de prosa, leido y con su codigo fuente enmascarado.

    Se arma una vez y se pasa a la regla: enmascarar de nuevo por regla
    duplicaria trabajo, y los numeros de linea podrian desincronizarse entre
    reglas si cada una tokenizara distinto.
    """

    def __init__(self, ruta):
        self.ruta = ruta
        self.crudo = _leer(ruta)
        self.bloques_codigo = [(m.start(), m.group(0)) for m in _FENCE.finditer(self.crudo)]
        self.prosa = _mascarar(self.crudo)
        self.lineas = self.prosa.splitlines()
        self.encabezados = _encabezados(self.prosa)


# ---------------------------------------------------------------------------
# Recursos: vocabulario declarado
# ---------------------------------------------------------------------------

def check_lista_palabras(doc, opts):
    """Word list: terminos fuera de la lista declarada por el proyecto.

    La guia mantiene su propio glosario y cada proyecto lo extiende con el
    suyo. Se declara con `--lista`, un JSON `{"termino": "alternativa"}`.
    """
    lista = _cargar_lista(opts.lista, '--lista')
    out = []
    for malo, bueno in lista.items():
        for linea, _t, coincidencia in _buscar(doc.prosa, [malo]):
            out.append((linea, '{!r}: usar {!r}'.format(coincidencia, bueno)))
    return out


def check_nombres_producto(doc, opts):
    """Product names: el nombre de producto se escribe como el proyecto lo declara.

    Declarado con `--productos`, un JSON con la grafia correcta de cada
    nombre. Busca variantes de mayusculas distintas a la declarada.
    """
    productos = _cargar_lista(opts.productos, '--productos')
    out = []
    for correcto in productos:
        for m in re.finditer(r'\b{}\b'.format(re.escape(correcto)), doc.prosa, re.I):
            if m.group(0) != correcto:
                linea = doc.prosa.count('\n', 0, m.start()) + 1
                out.append((linea, '{!r} deberia escribirse {!r}'
                            .format(m.group(0), correcto)))
    return out


# ---------------------------------------------------------------------------
# Principios generales
# ---------------------------------------------------------------------------

MINIMIZADORES = ('simply', 'simple', 'just', 'easy', 'easily', 'obviously', 'clearly')


def check_minimizadores(doc, opts):
    """Excessive claims: adjetivos que minimizan el esfuerzo del lector.

    "Simply click here" le dice al lector que algo dificil deberia serle
    facil; si no lo es, la documentacion lo hizo sentir torpe.
    """
    return [(linea, '{!r}: minimiza el esfuerzo del lector'.format(c))
            for linea, _t, c in _buscar(doc.prosa, MINIMIZADORES)]


def check_inclusivo(doc, opts):
    """Inclusive language: terminos fuera de la lista declarada.

    La guia da ejemplos (whitelist/blacklist, master/slave) y dice extender
    segun el dominio del proyecto. Se declara con `--inclusivo`.
    """
    lista = _cargar_lista(opts.inclusivo, '--inclusivo')
    return [(linea, 'termino no inclusivo: {!r}'.format(c))
            for linea, _t, c in _buscar(doc.prosa, lista)]


def check_jerga(doc, opts):
    """Jargon: terminos de jerga fuera de la lista declarada.

    La jerga es especifica de cada dominio, asi que no hay lista universal:
    se declara con `--jerga`.
    """
    lista = _cargar_lista(opts.jerga, '--jerga')
    return [(linea, 'jerga: {!r}'.format(c)) for linea, _t, c in _buscar(doc.prosa, lista)]


MARCAS_TEMPORALES = ('currently', 'now', 'soon', 'upcoming', 'recently', 'today')


def check_tiempo_relativo(doc, opts):
    """Timeless documentation: marcas de tiempo relativas al momento de escribir.

    "Currently" y "soon" envejecen mal: lo que es cierto hoy puede no serlo
    cuando se lea el documento.
    """
    return [(linea, '{!r}: marca de tiempo relativa al momento de escribir'.format(c))
            for linea, _t, c in _buscar(doc.prosa, MARCAS_TEMPORALES)]


# ---------------------------------------------------------------------------
# Lengua y gramatica
# ---------------------------------------------------------------------------

_ABREV_LATINAS = re.compile(r'\b(e\.g\.|i\.e\.|etc\.)', re.I)


def check_abreviaturas_latinas(doc, opts):
    """Abbreviations: evitar abreviaturas latinas, escribir en su lugar."""
    out = []
    for m in _ABREV_LATINAS.finditer(doc.prosa):
        linea = doc.prosa.count('\n', 0, m.start()) + 1
        out.append((linea, '{!r}: escribir "for example", "that is" o "and so on"'
                    .format(m.group(0))))
    return out


def check_encabezados_caja(doc, opts):
    """Capitalization: encabezados en minuscula de oracion, no en Title Case.

    Heuristica: se considera Title Case cuando dos o mas palabras de mas de
    tres letras, fuera de la primera, empiezan con mayuscula. No distingue
    nombres propios ni siglas, que legitimamente van en mayuscula: puede
    marcar de mas sobre un encabezado con varios nombres propios.
    """
    out = []
    for linea, _nivel, titulo in doc.encabezados:
        palabras = titulo.split()
        capitalizadas = sum(1 for p in palabras[1:]
                            if p[:1].isupper() and len(p) > 3 and not p.isupper())
        if capitalizadas >= 2:
            out.append((linea, 'encabezado en Title Case: {!r}'.format(titulo)))
    return out


def check_plural_parentesis(doc, opts):
    """Pluralization: nada de plurales entre parentesis, como "archivo(s)"."""
    out = []
    for m in re.finditer(r'\b\w+\(s\)', doc.prosa):
        linea = doc.prosa.count('\n', 0, m.start()) + 1
        out.append((linea, 'plural entre parentesis: {!r}'.format(m.group(0))))
    return out


def check_posesivo_producto(doc, opts):
    """Possessives: un nombre de producto no lleva posesivo.

    "Google Docs's" o "Google Docs'" son incorrectos: un nombre de producto
    se usa en aposicion ("the Google Docs interface"), no como dueno de algo.
    """
    productos = _cargar_lista(opts.productos, '--productos')
    out = []
    for nombre in productos:
        patron = re.compile(r"\b{}('s|s')\b".format(re.escape(nombre)))
        for m in patron.finditer(doc.prosa):
            linea = doc.prosa.count('\n', 0, m.start()) + 1
            out.append((linea, '{!r}: no se posesiviza un nombre de producto'
                        .format(m.group(0))))
    return out


def check_tiempo_futuro(doc, opts):
    """Present tense: preferir presente; "will" suele describir algo que ya pasa.

    Marca todo "will": no distingue un futuro real de una descripcion de
    comportamiento, asi que puede marcar de mas sobre frases que si necesitan
    tiempo futuro.
    """
    out = []
    for m in re.finditer(r'\bwill\b', doc.prosa, re.I):
        linea = doc.prosa.count('\n', 0, m.start()) + 1
        out.append((linea, '"will": preferir presente salvo que describa un '
                           'evento futuro real'))
    return out


PRONOMBRES_GENERO = ('he', 'she', 'him', 'her', 'his', 'hers', 'himself', 'herself')


def check_pronombres_genero(doc, opts):
    """Pronouns: evitar pronombres de genero cuando el genero no se conoce."""
    return [(linea, '{!r}: usar "they" o reformular sin pronombre'.format(c))
            for linea, _t, c in _buscar(doc.prosa, PRONOMBRES_GENERO)]


PRIMERA_PERSONA = ('we', "we're", "we've", 'our', 'us')


def check_primera_persona(doc, opts):
    """Second person: instrucciones en primera persona ("we", "our") en vez de "you"."""
    return [(linea, '{!r}: las instrucciones van en segunda persona ("you")'.format(c))
            for linea, _t, c in _buscar(doc.prosa, PRIMERA_PERSONA)]


# ---------------------------------------------------------------------------
# Puntuacion
# ---------------------------------------------------------------------------

def check_mayuscula_dos_puntos(doc, opts):
    """Colons: mayuscula despues de los dos puntos solo si sigue una oracion completa.

    Heuristica: si tras los dos puntos hay mas de cuatro palabras y la frase
    termina en punto, se exige mayuscula inicial. Una frase corta o una lista
    no lo exige: ahi la guia deja lugar al criterio, y el instrumento no pide
    nada.
    """
    out = []
    for m in re.finditer(r':\s+([a-zA-Z][^\n]*)', doc.prosa):
        resto = m.group(1)
        palabras = resto.split()
        if len(palabras) > 4 and resto.rstrip().endswith('.') and resto[:1].islower():
            linea = doc.prosa.count('\n', 0, m.start()) + 1
            out.append((linea, 'oracion completa tras los dos puntos sin '
                               'mayuscula inicial'))
    return out


_ENUM = re.compile(r'\b\w+(?:,\s\w+)+(,?)\s(and|or)\s\w+\b')


def check_coma_serial(doc, opts):
    """Commas: coma serial en toda enumeracion de tres elementos o mas."""
    out = []
    for m in _ENUM.finditer(doc.prosa):
        if m.group(1) != ',':
            linea = doc.prosa.count('\n', 0, m.start()) + 1
            out.append((linea, 'enumeracion sin coma serial antes de {!r}'
                        .format(m.group(2))))
    return out


_RAYA_MAL = re.compile(r'[ \t]—|—[ \t]')


def check_raya(doc, opts):
    """Dashes: la raya larga va pegada a las palabras, sin espacios alrededor."""
    out = []
    for m in _RAYA_MAL.finditer(doc.prosa):
        linea = doc.prosa.count('\n', 0, m.start()) + 1
        out.append((linea, 'raya con espacio alrededor'))
    return out


def check_puntos_suspensivos(doc, opts):
    """Ellipses: usar el caracter de elipsis (…), no tres puntos sueltos."""
    out = []
    for m in re.finditer(r'(?<!\.)\.\.\.(?!\.)', doc.prosa):
        linea = doc.prosa.count('\n', 0, m.start()) + 1
        out.append((linea, 'tres puntos sueltos en vez del caracter de elipsis'))
    return out


def check_parentesis_anidados(doc, opts):
    """Parentheses: nada de parentesis dentro de otro parentesis."""
    out = []
    profundidad = 0
    for i, ch in enumerate(doc.prosa):
        if ch == '(':
            if profundidad == 1:
                linea = doc.prosa.count('\n', 0, i) + 1
                out.append((linea, 'parentesis anidado'))
            profundidad += 1
        elif ch == ')':
            profundidad = max(0, profundidad - 1)
    return out


def check_punto_final(doc, opts):
    """Periods and end punctuation: un espacio despues del punto, no dos."""
    out = []
    for m in re.finditer(r'\w\.  +\w', doc.prosa):
        linea = doc.prosa.count('\n', 0, m.start()) + 1
        out.append((linea, 'dos o mas espacios despues del punto'))
    return out


def check_comillas_puntuacion(doc, opts):
    """Quotation marks: la coma y el punto van dentro de las comillas."""
    out = []
    for m in re.finditer(r'"[^"\n]*"[.,]', doc.prosa):
        linea = doc.prosa.count('\n', 0, m.start()) + 1
        out.append((linea, 'coma o punto fuera de las comillas'))
    return out


def check_and_or(doc, opts):
    """Slashes: "and/or" es ambiguo, y la barra usada como "o" tambien."""
    out = []
    for m in re.finditer(r'\band/or\b', doc.prosa, re.I):
        linea = doc.prosa.count('\n', 0, m.start()) + 1
        out.append((linea, '"and/or" es ambiguo: elegir uno o reformular'))
    for m in re.finditer(r'\b[a-zA-Z]+/[a-zA-Z]+\b', doc.prosa):
        if m.group(0).lower() == 'and/or':
            continue
        linea = doc.prosa.count('\n', 0, m.start()) + 1
        out.append((linea, '{!r}: la barra usada como "o" es ambigua'
                    .format(m.group(0))))
    return out


# ---------------------------------------------------------------------------
# Formato y organizacion
# ---------------------------------------------------------------------------

_FECHA_ORDINAL = re.compile(r'\b\d{1,2}(st|nd|rd|th)\b', re.I)


def check_fechas(doc, opts):
    """Dates and times: sin ordinales ("1st", "2nd") en las fechas."""
    out = []
    for m in _FECHA_ORDINAL.finditer(doc.prosa):
        linea = doc.prosa.count('\n', 0, m.start()) + 1
        out.append((linea, 'fecha con ordinal: {!r}'.format(m.group(0))))
    return out


def check_alt_texto(doc, opts):
    """Figures and other images: toda imagen tiene texto alternativo."""
    out = []
    for m in _IMAGE.finditer(doc.prosa):
        if not m.group(1).strip():
            linea = doc.prosa.count('\n', 0, m.start()) + 1
            out.append((linea, 'imagen sin texto alternativo'))
    return out


def check_notas_pie(doc, opts):
    """Footnotes: la guia desaconseja usarlas; preferir un enlace en el texto."""
    out = []
    for m in re.finditer(r'\[\^[^\]]+\]', doc.prosa):
        linea = doc.prosa.count('\n', 0, m.start()) + 1
        out.append((linea, 'nota al pie: {!r}'.format(m.group(0))))
    return out


def check_encabezados_unicos(doc, opts):
    """Headings and titles: encabezados unicos y sin punto final."""
    out = []
    vistos = {}
    for linea, _nivel, titulo in doc.encabezados:
        clave = titulo.strip().lower()
        if clave in vistos:
            out.append((linea, 'encabezado repetido: {!r} (ya en la linea {})'
                        .format(titulo, vistos[clave])))
        else:
            vistos[clave] = linea
        if titulo.rstrip().endswith('.'):
            out.append((linea, 'encabezado termina en punto: {!r}'.format(titulo)))
    return out


def check_items_lista(doc, opts):
    """Lists: los items empiezan con mayuscula y la puntuacion final es coherente."""
    out = []
    items = []
    for i, linea in enumerate(doc.lineas, start=1):
        m = re.match(r'^\s*[-*]\s+(.*\S)\s*$', linea)
        if m:
            items.append((i, m.group(1)))
    if not items:
        return out
    for linea, texto in items:
        if texto[:1].isalpha() and texto[:1].islower():
            out.append((linea, 'item de lista sin mayuscula inicial'))
    termina_en_punto = [texto.rstrip().endswith('.') for _l, texto in items]
    if any(termina_en_punto) and not all(termina_en_punto):
        out.append((items[0][0], 'la lista mezcla items con punto final y sin el'))
    return out


def check_notacion_matematica(doc, opts):
    """Mathematical notation: un solo estilo de notacion en el documento.

    Detecta el delimitador LaTeX (`$...$`) y avisa si ademas se usa `*` como
    signo de multiplicar fuera de esos delimitadores.
    """
    out = []
    if not re.search(r'\$[^$\n]+\$', doc.prosa):
        return out
    for m in re.finditer(r'\d\s*\*\s*\d', doc.prosa):
        linea = doc.prosa.count('\n', 0, m.start()) + 1
        out.append((linea, 'mezcla LaTeX ($...$) con "*" para multiplicar'))
    return out


def check_avisos_tipo(doc, opts):
    """Notes and other notices: el aviso usa uno de los tipos declarados.

    Reconoce la convencion **Tipo:** al principio de linea. Otras formas de
    marcar un aviso (un blockquote sin ese formato) no las ve.
    """
    tipos = _cargar_lista(opts.avisos, '--avisos')
    out = []
    for m in re.finditer(r'^\*\*(\w[\w ]*):\*\*\s', doc.prosa, re.M):
        palabra = m.group(1).strip()
        if palabra not in tipos:
            linea = doc.prosa.count('\n', 0, m.start()) + 1
            out.append((linea, 'tipo de aviso no declarado: {!r}'.format(palabra)))
    return out


_NUMERO_UNIDAD = re.compile(r'\d+\s?(kg|km|ms|mb|gb|kb|%|px|cm|mm|s|min|h)\b', re.I)


def check_numeros_chicos(doc, opts):
    """Numbers: los numeros del uno al nueve se escriben con letra.

    No aplica si el numero va pegado a una unidad. Alcance: solo texto
    corrido, no cubre parametros de API ni encabezados.
    """
    out = []
    for m in re.finditer(r'(?<![\w.])([1-9])(?![\w.])', doc.prosa):
        resto = doc.prosa[m.start():m.start() + 10]
        if _NUMERO_UNIDAD.match(resto):
            continue
        linea = doc.prosa.count('\n', 0, m.start()) + 1
        out.append((linea, 'numero {} deberia escribirse con letra'.format(m.group(1))))
    return out


_TELEFONO = re.compile(r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b')
_TELEFONO_RESERVADO = re.compile(r'555.?01\d{2}\b')


def check_telefonos(doc, opts):
    """Phone numbers: los telefonos de ejemplo usan el rango reservado 555-01XX."""
    out = []
    for m in _TELEFONO.finditer(doc.prosa):
        if not _TELEFONO_RESERVADO.search(m.group(0)):
            linea = doc.prosa.count('\n', 0, m.start()) + 1
            out.append((linea, 'telefono de ejemplo fuera del rango reservado: '
                               '{!r}'.format(m.group(0))))
    return out


_PASO = re.compile(r'^\s*\d+\.\s+(\S+)', re.M)


def check_procedimientos(doc, opts):
    """Procedures: los pasos numerados empiezan con un verbo.

    Heuristica: rechaza que el paso empiece con "You", "The", "This" o "It",
    que son sujetos y no verbos.
    """
    out = []
    for m in _PASO.finditer(doc.prosa):
        primera = m.group(1).strip('*_')
        if primera.lower() in ('you', 'the', 'this', 'it'):
            linea = doc.prosa.count('\n', 0, m.start()) + 1
            out.append((linea, 'paso no empieza con un verbo: {!r}'.format(primera)))
    return out


def check_tablas_encabezado(doc, opts):
    """Tables: toda tabla tiene fila separadora de encabezado."""
    out = []
    lineas = doc.lineas
    for i, linea in enumerate(lineas):
        if not linea.strip().startswith('|'):
            continue
        if i == 0 or not lineas[i - 1].strip().startswith('|'):
            if i + 1 >= len(lineas) or not re.match(r'^\s*\|?[\s:|-]+\|?\s*$', lineas[i + 1]):
                out.append((i + 1, 'tabla sin fila separadora de encabezado'))
    return out


_UNIDAD_PEGADA = re.compile(r'\b\d+(kg|km|ms|mb|gb|kb|px|cm|mm|min|h|s)\b', re.I)


def check_unidades(doc, opts):
    """Units of measurement: espacio entre el numero y la unidad."""
    out = []
    for m in _UNIDAD_PEGADA.finditer(doc.prosa):
        linea = doc.prosa.count('\n', 0, m.start()) + 1
        out.append((linea, 'unidad pegada al numero: {!r}'.format(m.group(0))))
    return out


# ---------------------------------------------------------------------------
# Enlaces
# ---------------------------------------------------------------------------

_ENLACE_PROHIBIDO = ('click here', 'here', 'this link', 'link', 'read more')


def check_texto_enlace(doc, opts):
    """Cross-references and linking: texto de enlace descriptivo, sin URL desnuda."""
    out = []
    for m in _LINK.finditer(doc.prosa):
        if m.group(1).strip().lower() in _ENLACE_PROHIBIDO:
            linea = doc.prosa.count('\n', 0, m.start()) + 1
            out.append((linea, 'texto de enlace no descriptivo: {!r}'.format(m.group(1))))
    for m in _BARE_URL.finditer(doc.prosa):
        linea = doc.prosa.count('\n', 0, m.start()) + 1
        out.append((linea, 'URL desnuda en el texto: {!r}'.format(m.group(0))))
    return out


def check_anclas(doc, opts):
    """Headings as link targets: todo enlace interno apunta a un encabezado que existe."""
    slugs = {_slug(t) for _l, _n, t in doc.encabezados}
    out = []
    for m in _LINK.finditer(doc.prosa):
        destino = m.group(2)
        if destino.startswith('#') and destino[1:] not in slugs:
            linea = doc.prosa.count('\n', 0, m.start()) + 1
            out.append((linea, 'enlace a un ancla que no existe: {!r}'.format(destino)))
    return out


# ---------------------------------------------------------------------------
# Interfaces de computadora
# ---------------------------------------------------------------------------

def check_bloques_codigo(doc, opts):
    """Code samples: largo de linea de los bloques de codigo y sin elisiones."""
    out = []
    for pos, bloque in doc.bloques_codigo:
        base = doc.crudo.count('\n', 0, pos) + 1
        for i, linea in enumerate(bloque.splitlines()):
            if linea.strip() in ('...', '# ...', '// ...'):
                out.append((base + i, 'elision con puntos suspensivos en un '
                                      'bloque de codigo'))
            if len(linea) > opts.ancho_codigo:
                out.append((base + i, 'linea de codigo de {} caracteres, el '
                                      'maximo es {}'.format(len(linea), opts.ancho_codigo)))
    return out


def check_sintaxis_cli(doc, opts):
    """Command-line syntax: opcional entre corchetes, no la palabra "(optional)"."""
    out = []
    for m in re.finditer(r'\((optional|required)\)', doc.prosa, re.I):
        linea = doc.prosa.count('\n', 0, m.start()) + 1
        out.append((linea, '{!r}: usar corchetes para lo opcional, no la palabra'
                    .format(m.group(0))))
    return out


def check_marcadores(doc, opts):
    """Placeholder formatting: los marcadores van en minusculas dentro de angulos.

    Marca los tokens en MAYUSCULAS que no esten precedidos por `<`. Puede
    confundir una sigla real (HTML, URL) con un marcador: es una heuristica.
    """
    out = []
    for m in re.finditer(r'\b[A-Z][A-Z0-9_]{2,}\b', doc.prosa):
        if doc.prosa[max(0, m.start() - 1):m.start()] == '<':
            continue
        linea = doc.prosa.count('\n', 0, m.start()) + 1
        out.append((linea, 'marcador de posicion en mayusculas: {!r} (usar '
                           '<minuscula-con-guiones>)'.format(m.group(0))))
    return out


_VERBOS_PROHIBIDOS = ('click on', 'hit enter', 'press the button')


def check_verbos_interaccion(doc, opts):
    """UI elements and interaction: verbos de interaccion desaconsejados."""
    out = []
    for frase in _VERBOS_PROHIBIDOS:
        for m in re.finditer(r'\b{}\b'.format(re.escape(frase)), doc.prosa, re.I):
            linea = doc.prosa.count('\n', 0, m.start()) + 1
            out.append((linea, '{!r}: preferir "click" o "select"'.format(m.group(0))))
    return out


# ---------------------------------------------------------------------------
# HTML y nombres
# ---------------------------------------------------------------------------

_TAG = re.compile(r'</?([a-zA-Z][a-zA-Z0-9]*)\b[^>]*>')


def check_html_en_markdown(doc, opts):
    """Markdown versus HTML: nada de HTML crudo dentro de un documento Markdown."""
    if not doc.ruta.endswith(('.md', '.markdown')):
        raise NoVerificable('la regla mide Markdown y el archivo no tiene esa extension')
    out = []
    for m in _TAG.finditer(doc.prosa):
        linea = doc.prosa.count('\n', 0, m.start()) + 1
        out.append((linea, 'etiqueta HTML dentro de un documento Markdown: {!r}'
                    .format(m.group(0))))
    return out


_DOMINIO = re.compile(r'\b[\w-]+\.(com|org|net|io|dev|co)\b', re.I)
_DOMINIOS_RESERVADOS = ('example.com', 'example.org', 'example.net', 'example.edu')


def check_dominios(doc, opts):
    """Example domains and names: usar los dominios reservados para ejemplos."""
    out = []
    for m in _DOMINIO.finditer(doc.prosa):
        if m.group(0).lower() not in _DOMINIOS_RESERVADOS:
            linea = doc.prosa.count('\n', 0, m.start()) + 1
            out.append((linea, 'dominio de ejemplo real: {!r}, usar example.com, '
                               '.org, .net o .edu'.format(m.group(0))))
    return out


_NOMBRE_ARCHIVO = re.compile(
    r'\b[\w][\w.-]*\.(png|jpg|jpeg|gif|svg|pdf|zip|html|css|md)\b', re.I)


def check_nombres_archivo(doc, opts):
    """Filenames: minusculas y con guiones, no guion bajo ni mayusculas.

    Alcanza a archivos de documentacion y de recursos (imagenes, paginas), no
    a codigo fuente: la convencion de nombres de un `.py` la fija el lenguaje,
    no esta guia.
    """
    out = []
    for m in _NOMBRE_ARCHIVO.finditer(doc.prosa):
        nombre = m.group(0)
        base = nombre.rsplit('.', 1)[0]
        if base != base.lower() or '_' in base:
            linea = doc.prosa.count('\n', 0, m.start()) + 1
            out.append((linea, 'nombre de archivo fuera de convencion: {!r}'
                        .format(nombre)))
    return out


RULES = {
    'abreviaturas-latinas': (check_abreviaturas_latinas, 'Abbreviations: abreviaturas latinas'),
    'alt-texto': (check_alt_texto, 'Figures: toda imagen tiene texto alternativo'),
    'anclas': (check_anclas, 'Headings as link targets: el ancla existe'),
    'and-or': (check_and_or, 'Slashes: "and/or" y la barra como "o"'),
    'avisos-tipo': (check_avisos_tipo, 'Notes and other notices: tipo declarado'),
    'bloques-codigo': (check_bloques_codigo, 'Code samples: largo de linea y sin elisiones'),
    'coma-serial': (check_coma_serial, 'Commas: coma serial en toda enumeracion'),
    'comillas-puntuacion': (check_comillas_puntuacion, 'Quotation marks: la puntuacion va adentro'),
    'dominios': (check_dominios, 'Example domains: rango reservado'),
    'encabezados-caja': (check_encabezados_caja, 'Capitalization: encabezados en minuscula de oracion'),
    'encabezados-unicos': (check_encabezados_unicos, 'Headings and titles: unicos y sin punto final'),
    'fechas': (check_fechas, 'Dates and times: sin ordinales'),
    'html-en-markdown': (check_html_en_markdown, 'Markdown versus HTML: sin HTML crudo'),
    'inclusivo': (check_inclusivo, 'Inclusive language: fuera de la lista declarada'),
    'items-lista': (check_items_lista, 'Lists: mayuscula inicial y puntuacion coherente'),
    'jerga': (check_jerga, 'Jargon: fuera de la lista declarada'),
    'lista-palabras': (check_lista_palabras, 'Word list: terminos fuera de la lista declarada'),
    'marcadores': (check_marcadores, 'Placeholder formatting: minusculas con guiones'),
    'mayuscula-dos-puntos': (check_mayuscula_dos_puntos, 'Colons: mayuscula tras una oracion completa'),
    'minimizadores': (check_minimizadores, 'Excessive claims: adjetivos que minimizan el esfuerzo'),
    'nombres-archivo': (check_nombres_archivo, 'Filenames: minusculas con guiones'),
    'nombres-producto': (check_nombres_producto, 'Product names: grafia declarada por el proyecto'),
    'notacion-matematica': (check_notacion_matematica, 'Mathematical notation: un solo estilo'),
    'notas-pie': (check_notas_pie, 'Footnotes: la guia las desaconseja'),
    'numeros-chicos': (check_numeros_chicos, 'Numbers: del uno al nueve con letra'),
    'parentesis-anidados': (check_parentesis_anidados, 'Parentheses: sin anidar'),
    'plural-parentesis': (check_plural_parentesis, 'Pluralization: plurales con "(s)"'),
    'posesivo-producto': (check_posesivo_producto, 'Possessives: posesivo sobre un nombre de producto'),
    'primera-persona': (check_primera_persona, 'Second person: primera persona en instrucciones'),
    'procedimientos': (check_procedimientos, 'Procedures: cada paso empieza con un verbo'),
    'pronombres-genero': (check_pronombres_genero, 'Pronouns: pronombres de genero'),
    'punto-final': (check_punto_final, 'Periods: un espacio despues del punto'),
    'puntos-suspensivos': (check_puntos_suspensivos, 'Ellipses: el caracter, no tres puntos sueltos'),
    'raya': (check_raya, 'Dashes: raya larga sin espacios'),
    'sintaxis-cli': (check_sintaxis_cli, 'Command-line syntax: corchetes, no "(optional)"'),
    'tablas-encabezado': (check_tablas_encabezado, 'Tables: fila de encabezado'),
    'telefonos': (check_telefonos, 'Phone numbers: rango reservado'),
    'texto-enlace': (check_texto_enlace, 'Cross-references: texto de enlace descriptivo'),
    'tiempo-futuro': (check_tiempo_futuro, 'Present tense: tiempo futuro evitable'),
    'tiempo-relativo': (check_tiempo_relativo, 'Timeless documentation: marcas de tiempo relativas'),
    'unidades': (check_unidades, 'Units of measurement: espacio entre numero y unidad'),
    'verbos-interaccion': (check_verbos_interaccion, 'UI elements: verbos de interaccion desaconsejados'),
}


def main(argv=None):
    """Corre la regla pedida sobre los archivos dados y devuelve el exit code."""
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--rule')
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--lista', help='JSON {termino: alternativa}, para lista-palabras')
    parser.add_argument('--productos', help='JSON con nombres de producto, para '
                                            'nombres-producto y posesivo-producto')
    parser.add_argument('--inclusivo', help='JSON con terminos no inclusivos')
    parser.add_argument('--jerga', help='JSON con jerga del dominio')
    parser.add_argument('--avisos', help='JSON con los tipos de aviso declarados')
    parser.add_argument('--ancho-codigo', type=int, default=80, dest='ancho_codigo')
    parser.add_argument('files', nargs='*')
    args = parser.parse_args(argv)

    if args.list:
        for nombre in sorted(RULES):
            print('{:22} {}'.format(nombre, RULES[nombre][1]))
        return 0

    if args.rule not in RULES:
        print('NO-VERIFICABLE: regla desconocida: {!r} (ver --list)'.format(args.rule))
        return 2
    if not args.files:
        print('NO-VERIFICABLE: no se indicaron archivos')
        return 2

    func, etiqueta = RULES[args.rule]
    violaciones = []
    for ruta in args.files:
        if not os.path.isfile(ruta):
            print('NO-VERIFICABLE: no existe {}'.format(ruta))
            return 2
        try:
            doc = Documento(ruta)
            for linea, detalle in func(doc, args):
                violaciones.append((ruta, linea, detalle))
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
