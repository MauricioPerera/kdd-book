#!/usr/bin/env python3
"""Instrumentos para los criterios medibles de WCAG 2.2.

Diez reglas para doce criterios: `contraste` y `toque` sirven a dos cada una,
que es lo que pasa cuando el autor da el mismo umbral en dos niveles de
conformidad distintos (AA y AAA).

    autocomplete       los campos de datos personales declaran su proposito
    autoplay           nada suena solo sin manera de pararlo
    contraste          la razon de contraste llega al minimo
    etiqueta           todo control de formulario tiene nombre accesible
    etiquetaennombre   el nombre accesible contiene la etiqueta visible
    idioma             la pagina declara su idioma
    movimiento         hay alternativa para quien pide menos movimiento
    nombrerol          los componentes con rol tienen nombre, y el aria existe
    saltar             hay como saltear los bloques repetidos
    toque              el area de toque llega al minimo

**Por que son doce y no 87, dicho aca y no en el README.** Los otros 75
criterios son tecnicas reales y no se miden, y el motivo esta en el grafo nodo
por nodo. El resumen: WCAG dice "testable" y quiere decir *que una persona
formada pueda decidir si se cumple*. 1.1.1 pide una alternativa textual que
cumpla "el proposito equivalente" — que el `alt` este es decidible, que sea
equivalente no lo decide ninguna medicion. Estos doce son los criterios donde el
autor nombro un **mecanismo**: un token, un atributo, una razon, un area.

**Verde aca no es "la pagina es accesible".** Es "estos doce mecanismos estan".
Decirlo importa mas que en cualquier otra familia del repositorio, porque en
accesibilidad la herramienta que da verde de mas hace dano: convence de que no
hay nada que revisar.

Usa el arbol de `html_checks`, que ya construye uno sobre `html.parser`. Dos
parsers de HTML en el mismo repositorio terminan discrepando — ya paso una vez
con la definicion de emisor de peticiones.

`contraste` y `toque` comparan valores **renderizados**, que el HTML no tiene.
Leen los estilos en linea, que si estan en el artefacto, y aceptan `--medidas`
con lo que el proyecto haya medido. Sin ninguno de los dos, exit 2: es la misma
salida que uso `http_checks` para no salir a la red.

Exit codes (convencion KDD):
  0  la propiedad se cumple
  1  no se cumple
  2  no se pudo verificar

Uso:
    python a11y_checks.py --rule idioma <pagina.html>
    python a11y_checks.py --rule contraste --min 4.5 --medidas colores.json <p.html>
    python a11y_checks.py --list
"""

__all__ = [
    'check_autocomplete',
    'check_autoplay',
    'check_contraste',
    'check_etiqueta',
    'check_etiquetaennombre',
    'check_idioma',
    'check_movimiento',
    'check_nombrerol',
    'check_saltar',
    'check_toque',
    'main',
]

import argparse
import json
import os
import re
import sys

from html_checks import NoVerificable, parsear

# Sobre que mide esta familia: una pagina HTML.
#
# Lo declara cada familia y no una lista en `memoria.py`, porque esa lista
# ya quedo vieja dos veces. `aplicar` elige por este campo que instrumentos
# puede correr sobre lo que le dieron; sin el, agregar una familia la deja
# afuera en silencio y nada falla.
ARTEFACTO = 'html'


# ---------------------------------------------------------------------------
# Vocabulario declarado
# ---------------------------------------------------------------------------

# Tokens de `autocomplete` que el propio criterio 1.3.5 enumera (seccion
# "Input Purposes for User Interface Components"). Es la lista del autor, no una
# heuristica: por eso se puede exigir pertenencia y no parecido.
TOKENS = frozenset("""
name honorific-prefix given-name additional-name family-name honorific-suffix
nickname organization-title username new-password current-password organization
street-address address-line1 address-line2 address-line3 address-level4
address-level3 address-level2 address-level1 country country-name postal-code
cc-name cc-given-name cc-additional-name cc-family-name cc-number cc-exp
cc-exp-month cc-exp-year cc-csc cc-type transaction-currency transaction-amount
language bday bday-day bday-month bday-year sex url photo tel tel-country-code
tel-national tel-area-code tel-local tel-local-prefix tel-local-suffix
tel-extension email impp
""".split())

# Tipos de campo que piden datos del usuario por definicion del propio tipo.
# Un `type="text"` que en realidad pide un telefono no lo ve esta regla, y eso
# esta dicho en check_autocomplete: el alcance es lo que el marcado declara.
TIPOS_PERSONALES = ('email', 'tel')

CONTROLES = ('input', 'select', 'textarea')

# Tipos de input que no piden nada al usuario y por eso no necesitan etiqueta.
SIN_ETIQUETA = ('hidden', 'submit', 'reset', 'button', 'image')

# Roles que solo significan algo con un nombre accesible: son los que la
# tecnologia de asistencia anuncia por su nombre.
ROLES_CON_NOMBRE = ('button', 'link', 'checkbox', 'radio', 'textbox', 'combobox',
                    'listbox', 'menuitem', 'menuitemcheckbox', 'menuitemradio',
                    'tab', 'switch', 'slider', 'searchbox', 'spinbutton',
                    'treeitem', 'dialog', 'alertdialog')

# Atributos ARIA que existen. Una lista cerrada es lo unico que permite marcar
# un `aria-` inventado, que es un error mudo: no rompe nada y no hace nada.
ARIA = frozenset("""
aria-activedescendant aria-atomic aria-autocomplete aria-braillelabel
aria-brailleroledescription aria-busy aria-checked aria-colcount aria-colindex
aria-colindextext aria-colspan aria-controls aria-current aria-describedby
aria-description aria-details aria-disabled aria-errormessage aria-expanded
aria-flowto aria-haspopup aria-hidden aria-invalid aria-keyshortcuts aria-label
aria-labelledby aria-level aria-live aria-modal aria-multiline aria-multiselectable
aria-orientation aria-owns aria-placeholder aria-posinset aria-pressed
aria-readonly aria-relevant aria-required aria-roledescription aria-rowcount
aria-rowindex aria-rowindextext aria-rowspan aria-selected aria-setsize
aria-sort aria-valuemax aria-valuemin aria-valuenow aria-valuetext
""".split())

MEDIA = ('audio', 'video')

# BCP 47 en su forma minima: una subetiqueta primaria de 2 o 3 letras y despues
# subetiquetas alfanumericas. No valida contra el registro de IANA —eso pediria
# el registro— y por eso acepta `xx`; lo que descarta es lo que se ve en la
# practica: vacio, "espanol", "es_AR" con guion bajo.
IDIOMA = re.compile(r'^[A-Za-z]{2,3}(-[A-Za-z0-9]{1,8})*$')

HEX = re.compile(r'^#(?:([0-9a-f])([0-9a-f])([0-9a-f])|'
                 r'([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2}))$', re.I)
RGB = re.compile(r'^rgba?\(\s*(\d+)\D+(\d+)\D+(\d+)', re.I)

_DECLARACION = re.compile(r'([a-z-]+)\s*:\s*([^;]+)')
_PX = re.compile(r'^\s*(\d+(?:\.\d+)?)\s*px\s*$', re.I)


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def _estilo(elemento):
    """Las declaraciones del atributo `style`, como diccionario."""
    return {k.strip().lower(): v.strip()
            for k, v in _DECLARACION.findall(elemento.attrs.get('style', '').lower())}


def _color(texto):
    """Un color CSS a (r, g, b). Lanza NoVerificable si no lo sabe leer."""
    texto = texto.strip().lower()
    m = HEX.match(texto)
    if m:
        if m.group(1):
            return tuple(int(c * 2, 16) for c in m.group(1, 2, 3))
        return tuple(int(c, 16) for c in m.group(4, 5, 6))
    m = RGB.match(texto)
    if m:
        return tuple(int(m.group(i)) for i in (1, 2, 3))
    raise NoVerificable(
        'no se pudo leer el color {!r}. La regla entiende #rgb, #rrggbb y '
        'rgb(): un nombre CSS pediria la tabla de nombres, y adivinarlo seria '
        'peor que decir que no se puede'.format(texto))


def _luminancia(rgb):
    canales = []
    for valor in rgb:
        c = valor / 255.0
        canales.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * canales[0] + 0.7152 * canales[1] + 0.0722 * canales[2]


def _razon(frente, fondo):
    a, b = _luminancia(frente), _luminancia(fondo)
    claro, oscuro = max(a, b), min(a, b)
    return (claro + 0.05) / (oscuro + 0.05)


def _medidas(opts):
    """El JSON declarado por el proyecto, o {} si no declaro ninguno."""
    if not opts.medidas:
        return {}
    ruta = opts.medidas
    if not os.path.isfile(ruta):
        raise NoVerificable('las medidas declaradas no existen: {}'.format(ruta))
    try:
        with open(ruta, 'r', encoding='utf-8') as fh:
            return json.load(fh)
    except ValueError as exc:
        raise NoVerificable('medidas ilegibles: {}'.format(exc))


def _nombre_accesible(elemento, por_id):
    """El nombre que una tecnologia de asistencia anunciaria, o ''.

    Cubre las cuatro fuentes que se pueden resolver leyendo el documento:
    `aria-label`, `aria-labelledby`, un `<label for>` que apunte al control y un
    `<label>` que lo envuelva. El `title` queda afuera a proposito: el propio
    W3C lo desaconseja como unica fuente.
    """
    if elemento.attrs.get('aria-label', '').strip():
        return elemento.attrs['aria-label'].strip()
    referencia = elemento.attrs.get('aria-labelledby', '').strip()
    if referencia:
        textos = [por_id[i].texto_visible() for i in referencia.split() if i in por_id]
        if any(textos):
            return ' '.join(t for t in textos if t)
    propio = elemento.attrs.get('id')
    if propio:
        for etiqueta in por_id.get('__labels__', []):
            if etiqueta.attrs.get('for') == propio and etiqueta.texto_visible():
                return etiqueta.texto_visible()
    for ancestro in elemento.ancestros():
        if ancestro.tag == 'label' and ancestro.texto_visible():
            return ancestro.texto_visible()
    return ''


def _indice(elementos):
    por_id = {e.attrs['id']: e for e in elementos if e.attrs.get('id')}
    por_id['__labels__'] = [e for e in elementos if e.tag == 'label']
    return por_id


def _es_control(elemento):
    if elemento.tag not in CONTROLES:
        return False
    return elemento.attrs.get('type', 'text').lower() not in SIN_ETIQUETA


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_autocomplete(elementos, opts):
    """1.3.5: los campos que piden datos del usuario declaran su proposito.

    Dos mitades, las dos decidibles. Un `autocomplete` presente tiene que usar
    un token de la lista que el propio criterio enumera —por eso se puede exigir
    pertenencia y no parecido—, y un campo de un tipo que pide datos personales
    por definicion (`email`, `tel`) tiene que declararlo.

    Alcance: un `type="text"` que en realidad pide un telefono no lo ve. Saber
    que pide un campo de texto es leer su etiqueta y entenderla, que es
    exactamente la clase de juicio que deja a los otros 75 criterios en pila B.
    """
    out = []
    for e in elementos:
        if e.tag != 'input':
            continue
        tipo = e.attrs.get('type', 'text').lower()
        declarado = e.attrs.get('autocomplete', '').strip().lower()
        if declarado:
            tokens = [t for t in declarado.split() if t not in ('shipping', 'billing')]
            invalidos = [t for t in tokens if t not in TOKENS and t != 'off' and t != 'on']
            if invalidos:
                out.append((e.linea, 'autocomplete={!r}: {} no esta en la lista de '
                                     'tokens del criterio'
                            .format(declarado, ', '.join(invalidos))))
        elif tipo in TIPOS_PERSONALES:
            out.append((e.linea, '<input type="{}"> pide un dato personal y no '
                                 'declara su autocomplete'.format(tipo)))
    return out


def check_autoplay(elementos, opts):
    """1.4.2: nada suena solo sin manera de pararlo.

    Marca el medio con `autoplay` que ademas no esta `muted` y no ofrece
    `controls`. El criterio habla de audio que suena mas de tres segundos, y la
    duracion no esta en el marcado: la regla es conservadora a proposito, porque
    del lado de marcar de mas el costo es revisar, y del otro es una pagina que
    habla sola encima de un lector de pantalla.
    """
    out = []
    for e in elementos:
        if e.tag not in MEDIA or 'autoplay' not in e.attrs:
            continue
        if 'muted' in e.attrs or 'controls' in e.attrs:
            continue
        out.append((e.linea, '<{}> arranca solo, con sonido y sin controles: no hay '
                             'como pararlo'.format(e.tag)))
    return out


def _pares_de_contraste(elementos, opts):
    """(etiqueta, linea, frente, fondo, grande) de cada par que se pueda leer."""
    pares = []
    for e in elementos:
        estilo = _estilo(e)
        if 'color' in estilo and 'background-color' in estilo:
            grande = False
            tam = _PX.match(estilo.get('font-size', ''))
            if tam:
                grande = float(tam.group(1)) >= 24
            pares.append(('<{}>'.format(e.tag), e.linea,
                          _color(estilo['color']), _color(estilo['background-color']),
                          grande))
    for nombre, datos in sorted(_medidas(opts).items()):
        pares.append((nombre, 0, _color(datos['color']), _color(datos['fondo']),
                      bool(datos.get('grande'))))
    return pares


def check_contraste(elementos, opts):
    """1.4.3 y 1.4.6: la razon de contraste llega al minimo.

    El umbral es del autor y no admite discusion: 4.5:1 en AA, 7:1 en AAA, con
    la version relajada para texto grande. La cuenta es la formula de
    luminancia relativa de la propia norma.

    Y es, junto con `toque`, el caso que mejor muestra que operacionalizar no
    alcanza: **el umbral es perfecto y lo que compara no esta en el HTML**. Se
    leen los estilos en linea, que si estan en el artefacto, y lo que el
    proyecto haya medido y declarado en `--medidas`. Sin nada de eso, exit 2.
    """
    # 21:1 es el maximo posible —negro puro sobre blanco puro— asi que un
    # minimo mayor no lo cumple ninguna pagina. Cuando aparece, casi siempre es
    # el umbral de `toque` en pixeles pasado por error a esta regla, porque las
    # dos comparten `--min`. Sin esto el instrumento se pone rojo sobre paginas
    # impecables y el mensaje no da ninguna pista.
    if opts.min > 21.0:
        raise NoVerificable(
            'el minimo pedido es {}:1 y el maximo posible es 21:1 (negro sobre '
            'blanco). Si eso era un area de toque en pixeles, la regla es '
            '`toque`'.format(opts.min))

    pares = _pares_de_contraste(elementos, opts)
    if not pares:
        raise NoVerificable(
            'no hay ningun par de colores que leer. El contraste compara valores '
            'renderizados, y el HTML solo trae los estilos en linea: el proyecto '
            'declara el resto con --medidas, igual que declara sus capturas para '
            'http_checks')

    out = []
    for etiqueta, linea, frente, fondo, grande in pares:
        minimo = opts.min_grande if grande else opts.min
        razon = _razon(frente, fondo)
        if razon + 1e-9 < minimo:
            out.append((linea, '{}: contraste {:.2f}:1, el minimo es {}:1{}'
                        .format(etiqueta, razon, minimo,
                                ' (texto grande)' if grande else '')))
    return out


def check_etiqueta(elementos, opts):
    """3.3.2: todo control de formulario tiene nombre accesible.

    Un control sin nombre se anuncia como "cuadro de edicion" y nada mas. Se
    aceptan las cuatro fuentes que se resuelven leyendo el documento; el
    `placeholder` no cuenta, y no es un descuido: desaparece al escribir.
    """
    por_id = _indice(elementos)
    return [(e.linea, '<{}> no tiene etiqueta ni nombre accesible'.format(e.tag))
            for e in elementos
            if _es_control(e) and not _nombre_accesible(e, por_id)]


def check_etiquetaennombre(elementos, opts):
    """2.5.3: el nombre accesible contiene la etiqueta visible.

    Es el criterio mas decidible de los 87: dos cadenas y una comparacion. Y el
    defecto que evita es concreto — si el boton dice "Buscar" y su `aria-label`
    dice "Enviar formulario", quien usa la voz para navegar dice "buscar" y no
    pasa nada.

    Solo mira los controles que tienen `aria-label` Y texto visible: sin las dos
    cosas no hay nada que comparar.
    """
    out = []
    for e in elementos:
        etiqueta = e.attrs.get('aria-label', '').strip()
        visible = e.texto_visible()
        if not etiqueta or not visible:
            continue
        if visible.lower() not in etiqueta.lower():
            out.append((e.linea, '<{}> se ve "{}" y su nombre accesible es "{}": '
                                 'quien lo nombra en voz alta no lo activa'
                        .format(e.tag, visible, etiqueta)))
    return out


def check_idioma(elementos, opts):
    """3.1.1: la pagina declara su idioma.

    Sin `lang`, el lector de pantalla lee con la fonetica que tenga puesta. La
    validacion es de forma, no contra el registro de IANA: acepta `xx`, y
    descarta lo que se ve en la practica —vacio, "espanol", `es_AR`—.
    """
    raices = [e for e in elementos if e.tag == 'html']
    if not raices:
        raise NoVerificable('el documento no tiene <html>: puede ser un fragmento, '
                            'y un fragmento no declara idioma de pagina')
    declarado = raices[0].attrs.get('lang', '').strip()
    if not declarado:
        return [(raices[0].linea, '<html> no declara lang')]
    if not IDIOMA.match(declarado):
        return [(raices[0].linea, 'lang={!r} no tiene forma de etiqueta de idioma'
                 .format(declarado))]
    return []


def check_movimiento(elementos, opts):
    """2.3.3: hay alternativa para quien pide menos movimiento.

    Si los estilos declaran animaciones o transiciones, tiene que haber un
    bloque `prefers-reduced-motion: reduce`. Lee los `<style>` del documento y
    las hojas que el proyecto declare con `--estilos`.

    No comprueba que el bloque desactive TODAS las animaciones: eso pide
    resolver la cascada. Verde aca es "hay alternativa declarada".
    """
    # `.texto` y no `texto_visible()`: ese metodo se saltea `style` a proposito
    # —su contenido no lo ve nadie y contarlo daria nombre accesible a elementos
    # que no lo tienen— y aca hace falta justo lo contrario, el CSS crudo.
    css = ' '.join(e.texto for e in elementos if e.tag == 'style')
    for ruta in opts.estilos:
        if not os.path.isfile(ruta):
            raise NoVerificable('la hoja declarada no existe: {}'.format(ruta))
        with open(ruta, 'r', encoding='utf-8') as fh:
            css += ' ' + fh.read()
    if not css.strip():
        raise NoVerificable(
            'no hay estilos que leer: el criterio habla de animaciones, que viven '
            'en el CSS. El proyecto declara sus hojas con --estilos')

    plano = css.lower()
    if not re.search(r'\b(animation|transition)\b', plano):
        return []
    if 'prefers-reduced-motion' in plano:
        return []
    return [(0, 'los estilos declaran animaciones y no hay ningun bloque '
                'prefers-reduced-motion: reduce')]


def check_nombrerol(elementos, opts):
    """4.1.2: los componentes con rol tienen nombre, y el aria que usan existe.

    Dos mitades decidibles. Un elemento con un `role` que la tecnologia de
    asistencia anuncia por su nombre tiene que tener uno. Y un atributo
    `aria-cualquiercosa` que no existe es un error mudo: no rompe nada, no hace
    nada, y nadie se entera. Por eso la lista de atributos es cerrada.
    """
    por_id = _indice(elementos)
    out = []
    for e in elementos:
        rol = e.attrs.get('role', '').strip().lower()
        if rol in ROLES_CON_NOMBRE and not _nombre_accesible(e, por_id) \
                and not e.texto_visible():
            out.append((e.linea, '<{} role="{}"> no tiene nombre accesible: se '
                                 'anuncia como un {} sin nombre'
                        .format(e.tag, rol, rol)))
        for atributo in sorted(e.attrs):
            if atributo.startswith('aria-') and atributo not in ARIA:
                out.append((e.linea, '{}: ese atributo aria no existe, asi que no '
                                     'hace nada y nadie avisa'.format(atributo)))
    return out


def check_saltar(elementos, opts):
    """2.4.1: hay como saltear los bloques repetidos.

    Sirve un enlace de salto —un `<a href="#x">` cuyo destino exista— o una
    region principal, que es el mecanismo moderno para lo mismo. Basta uno.
    """
    ids = {e.attrs['id'] for e in elementos if e.attrs.get('id')}
    for e in elementos:
        if e.tag == 'main' or e.attrs.get('role', '').lower() == 'main':
            return []
        if e.tag == 'a':
            destino = e.attrs.get('href', '')
            if destino.startswith('#') and destino[1:] in ids:
                return []
    return [(0, 'no hay enlace de salto con destino existente ni region principal: '
                'quien navega con teclado recorre el encabezado en cada pagina')]


def check_toque(elementos, opts):
    """2.5.5 y 2.5.8: el area de toque llega al minimo.

    24 por 24 pixeles CSS en AA, 44 por 44 en AAA. Mismo problema que
    `contraste` y misma salida: se leen los tamanos en linea y lo que el
    proyecto declare en `--medidas`. El criterio tiene excepciones —objetivos en
    linea con el texto, entre otras— que esta regla no distingue, asi que puede
    marcar de mas; esta dicho porque marcar de mas en accesibilidad cuesta una
    revision y marcar de menos cuesta una barrera.
    """
    objetivos = []
    for e in elementos:
        estilo = _estilo(e)
        ancho, alto = _PX.match(estilo.get('width', '')), _PX.match(estilo.get('height', ''))
        if ancho and alto:
            objetivos.append(('<{}>'.format(e.tag), e.linea,
                              float(ancho.group(1)), float(alto.group(1))))
    for nombre, datos in sorted(_medidas(opts).items()):
        objetivos.append((nombre, 0, float(datos['ancho']), float(datos['alto'])))

    if not objetivos:
        raise NoVerificable(
            'no hay ninguna medida que leer. El area de toque es un valor '
            'renderizado: el proyecto lo declara con --medidas, igual que declara '
            'sus capturas para http_checks')

    return [(linea, '{}: {:.0f} por {:.0f}, el minimo es {} por {}'
             .format(nombre, ancho, alto, opts.min, opts.min))
            for nombre, linea, ancho, alto in objetivos
            if ancho < opts.min or alto < opts.min]


RULES = {
    'autocomplete': (check_autocomplete, 'Proposito del campo: los datos personales lo declaran'),
    'autoplay': (check_autoplay, 'Control de audio: nada suena solo sin como pararlo'),
    'contraste': (check_contraste, 'Contraste: la razon llega al minimo'),
    'etiqueta': (check_etiqueta, 'Etiquetas: todo control tiene nombre accesible'),
    'etiquetaennombre': (check_etiquetaennombre, 'Etiqueta en el nombre: el nombre accesible la contiene'),
    'idioma': (check_idioma, 'Idioma: la pagina declara el suyo'),
    'movimiento': (check_movimiento, 'Animacion: hay alternativa para quien pide menos movimiento'),
    'nombrerol': (check_nombrerol, 'Nombre y rol: los componentes tienen nombre y el aria existe'),
    'saltar': (check_saltar, 'Saltar bloques: hay como saltear lo repetido'),
    'toque': (check_toque, 'Area de toque: llega al minimo'),
}


def main(argv=None):
    """Corre la regla pedida sobre los archivos dados y devuelve el exit
    code.
    """
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--rule')
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--min', type=float, default=4.5,
                        help='umbral: razon de contraste, o pixeles de area de toque')
    parser.add_argument('--min-grande', type=float, default=3.0,
                        help='razon de contraste exigida al texto grande')
    parser.add_argument('--medidas', help='JSON con los valores renderizados que midio el proyecto')
    parser.add_argument('--estilos', action='append', default=[],
                        help='hoja de estilos a leer, repetible')
    parser.add_argument('files', nargs='*')
    args = parser.parse_args(argv)

    if args.list:
        for nombre in sorted(RULES):
            print('{:17} {}'.format(nombre, RULES[nombre][1]))
        return 0

    if args.rule not in RULES:
        print('NO-VERIFICABLE: regla desconocida: {!r} (ver --list)'.format(args.rule))
        return 2
    if not args.files:
        print('NO-VERIFICABLE: no se indicaron paginas')
        return 2

    func, etiqueta = RULES[args.rule]
    violaciones = []
    for ruta in args.files:
        if not os.path.isfile(ruta):
            print('NO-VERIFICABLE: no existe {}'.format(ruta))
            return 2
        try:
            for linea, detalle in func(parsear(ruta), args):
                violaciones.append((ruta, linea, detalle))
        except NoVerificable as exc:
            print('NO-VERIFICABLE: {}: {}'.format(etiqueta, exc))
            return 2
        except (OSError, KeyError, TypeError, ValueError) as exc:
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
