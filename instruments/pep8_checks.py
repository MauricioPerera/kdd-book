#!/usr/bin/env python3
"""Instrumentos de PEP 8: forma superficial de un archivo Python.

Familia mas grande del repositorio, 27 reglas, y existe por el hallazgo que dejo
la septima fuente: **compartir artefacto no es compartir medicion**. PEP 8 habla
del mismo archivo Python que Codigo Limpio y `checks.py` no le sirve casi nada,
porque `checks.py` mide estructura y significado —duplicacion, codigo muerto,
envidia de caracteristicas— y esto mide **forma**: sangria, lineas en blanco,
orden de imports, CapWords.

Las dos que si comparten estan afuera a proposito: largo de linea y tabuladores
ya los mide `repo_checks.py --rule g24`, que Martin llama "seguir las
convenciones estandar". G24 ya era un pedazo de PEP 8 sin decirlo, y duplicarlo
aca daria dos instrumentos que pueden discrepar sobre el mismo umbral.

**Dos herramientas y no una, y el motivo importa.** Lo de forma se mide con
`tokenize` y no con expresiones regulares sobre las lineas: un `#` adentro de un
string no es un comentario, y un regex no lo sabe. Lo de nombres se mide sobre
el AST. Cada regla dice cual usa.

**Lo que estas reglas no miran.** El orden de los grupos de imports —estandar,
terceros, local— pide saber que paquete es de terceros, y eso vive en el
manifiesto y no en el archivo: es el mismo dato que `entorno_checks` pide
declarar. `check_imports` mide lo que si esta en el archivo.

Exit codes (convencion KDD):
  0  la propiedad se cumple
  1  no se cumple
  2  no se pudo verificar

Uso:
    python pep8_checks.py --rule sangria <archivo.py>
    python pep8_checks.py --list
"""

import argparse
import ast
import io
import keyword
import os
import re
import sys
import token as token_mod
import tokenize

# Sobre que mide esta familia: un archivo .py suelto: no necesita contexto.
#
# Lo declara cada familia y no una lista en `memoria.py`, porque esa lista
# ya quedo vieja dos veces. `aplicar` elige por este campo que instrumentos
# puede correr sobre lo que le dieron; sin el, agregar una familia la deja
# afuera en silencio y nada falla.
ARTEFACTO = 'archivo-python'


class NoVerificable(Exception):
    """Falta el dato sin el cual la regla no se puede evaluar (exit 2)."""


CAPWORDS = re.compile(r'^_{0,2}[A-Z][a-zA-Z0-9]*_{0,2}$')
SNAKE = re.compile(r'^_{0,2}[a-z][a-z0-9_]*_{0,2}$')
MAYUSCULAS = re.compile(r'^_{0,2}[A-Z][A-Z0-9_]*$')
MODULO = re.compile(r'^[a-z][a-z0-9_]*$')

AMBIGUOS = ('l', 'O', 'I')

COOKIE = re.compile(r'coding[:=]\s*([-\w.]+)')

# Operadores binarios con los que una linea no puede terminar: PEP 8 pide
# cortar ANTES del operador, siguiendo a Knuth.
BINARIOS = ('+', '-', '*', '/', '//', '%', '@', '**', '<<', '>>', '&', '|', '^',
            '<', '>', '<=', '>=', '==', '!=', 'and', 'or', 'in', 'is')

ABRE = ('(', '[', '{')
CIERRA = (')', ']', '}')


# ---------------------------------------------------------------------------
# Lectura
# ---------------------------------------------------------------------------

class Fuente:
    """Un archivo leido de las tres maneras que hacen falta.

    Se arma una vez y se le pasa a la regla. Sin esto cada regla volveria a
    leer, tokenizar y parsear el mismo archivo, y las tres lecturas podrian
    desincronizarse entre reglas.
    """

    def __init__(self, ruta):
        self.ruta = ruta
        self.crudo = self._leer()
        self.lineas = self.crudo.splitlines()
        self.arbol = self._parsear()
        self.tokens = self._tokenizar()

    def _leer(self):
        try:
            with open(self.ruta, 'rb') as fh:
                bruto = fh.read()
        except OSError as exc:
            raise NoVerificable('no se pudo leer {}: {}'.format(self.ruta, exc))
        try:
            return bruto.decode('utf-8')
        except UnicodeDecodeError as exc:
            raise NoVerificable(
                'el archivo no decodifica como UTF-8: {}. Sin poder leerlo no se '
                'puede medir nada de su forma'.format(exc))

    def _parsear(self):
        try:
            return ast.parse(self.crudo, filename=self.ruta)
        except SyntaxError as exc:
            raise NoVerificable(
                'el archivo no es Python valido ({}): la forma de un archivo que '
                'no compila no dice nada'.format(exc))

    def _tokenizar(self):
        try:
            return list(tokenize.generate_tokens(io.StringIO(self.crudo).readline))
        except (tokenize.TokenError, IndentationError) as exc:
            raise NoVerificable('no se pudo tokenizar: {}'.format(exc))

    def significativos(self):
        """Tokens que no son ruido de formato."""
        return [t for t in self.tokens
                if t.type not in (token_mod.NEWLINE, token_mod.NL,
                                  token_mod.INDENT, token_mod.DEDENT,
                                  token_mod.ENDMARKER)]

    def linea(self, numero):
        return self.lineas[numero - 1] if 0 < numero <= len(self.lineas) else ''


def _defs(arbol):
    for nodo in ast.walk(arbol):
        if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield nodo


def _clases(arbol):
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.ClassDef):
            yield nodo


def _metodos(arbol):
    """(clase, metodo) de cada funcion definida directamente en una clase."""
    for clase in _clases(arbol):
        for cuerpo in clase.body:
            if isinstance(cuerpo, (ast.FunctionDef, ast.AsyncFunctionDef)):
                yield clase, cuerpo


def _asignaciones_de_modulo(arbol):
    """(linea, nombre, valor) de cada asignacion en el nivel del modulo."""
    for nodo in arbol.body:
        if isinstance(nodo, ast.Assign):
            objetivos, valor = nodo.targets, nodo.value
        elif isinstance(nodo, ast.AnnAssign):
            objetivos, valor = [nodo.target], nodo.value
        else:
            continue
        for objetivo in objetivos:
            if isinstance(objetivo, ast.Name):
                yield nodo.lineno, objetivo.id, valor


def _es_literal(valor):
    if isinstance(valor, ast.Constant):
        return True
    if isinstance(valor, (ast.Tuple, ast.List, ast.Set)):
        return all(isinstance(e, ast.Constant) for e in valor.elts)
    return False


def _decorado(nodo, nombres):
    for decorador in nodo.decorator_list:
        if isinstance(decorador, ast.Name) and decorador.id in nombres:
            return True
        if isinstance(decorador, ast.Attribute) and decorador.attr in nombres:
            return True
    return False


def _primera_linea(nodo):
    """La linea donde empieza la definicion, decoradores incluidos."""
    if nodo.decorator_list:
        return min(d.lineno for d in nodo.decorator_list)
    return nodo.lineno


# ---------------------------------------------------------------------------
# Disposicion del codigo
# ---------------------------------------------------------------------------

def check_sangria(fuente, opts):
    """PEP 8 "Indentation": cuatro espacios por nivel.

    Mira los tokens INDENT, que son la sangria **logica**: las lineas de
    continuacion se alinean con el delimitador de apertura y ahi el multiplo de
    cuatro no aplica. Un regex sobre las lineas no distingue las dos cosas.
    """
    out = []
    for t in fuente.tokens:
        if t.type != token_mod.INDENT:
            continue
        if '\t' in t.string:
            continue        # los tabuladores los mide g24
        if len(t.string) % 4:
            out.append((t.start[0], 'sangria de {} espacios: no es multiplo de cuatro'
                        .format(len(t.string))))
    return out


def check_operador(fuente, opts):
    """PEP 8 "Should a Line Break Before or After a Binary Operator?": antes.

    Una linea de continuacion no puede terminar en el operador. Se mira el
    ultimo token significativo de cada linea fisica que no sea la ultima de su
    linea logica.
    """
    out = []
    ultimo_por_linea = {}
    for t in fuente.significativos():
        if t.type in (token_mod.COMMENT,):
            continue
        ultimo_por_linea[t.end[0]] = t
    for numero, t in sorted(ultimo_por_linea.items()):
        if t.string in BINARIOS and numero < len(fuente.lineas):
            out.append((numero, 'la linea termina en {!r}: el corte va ANTES del '
                                'operador'.format(t.string)))
    return out


def check_blancos(fuente, opts):
    """PEP 8 "Blank Lines": dos entre definiciones de nivel superior, una entre metodos.

    Se cuentan las lineas en blanco que preceden a cada definicion. La primera
    del archivo y la primera de una clase no piden nada: no hay nada arriba de
    lo que separarlas.
    """
    metodos = {id(m) for _c, m in _metodos(fuente.arbol)}
    # Las dos lineas en blanco son para las definiciones de NIVEL SUPERIOR. Una
    # funcion anidada no pide ninguna: PEP 8 dice para adentro de una funcion
    # "usar lineas en blanco con moderacion, para marcar secciones logicas".
    # Sin esta distincion la regla marcaba en rojo un `_reemplazo` de tres
    # lineas metido adentro de su unica llamadora, que es justo el caso donde
    # separar seria peor.
    de_nivel_superior = {id(n) for n in fuente.arbol.body}
    cuerpo_de_clase = {}
    for clase in _clases(fuente.arbol):
        for i, cuerpo in enumerate(clase.body):
            cuerpo_de_clase[id(cuerpo)] = i

    out = []
    for nodo in list(_defs(fuente.arbol)) + list(_clases(fuente.arbol)):
        inicio = _primera_linea(nodo)
        if inicio <= 1:
            continue
        if id(nodo) in cuerpo_de_clase and cuerpo_de_clase[id(nodo)] == 0:
            continue
        if id(nodo) not in de_nivel_superior and id(nodo) not in metodos:
            continue
        esperadas = 1 if id(nodo) in metodos else 2
        blancas = 0
        numero = inicio - 1
        while numero >= 1 and not fuente.linea(numero).strip():
            blancas += 1
            numero -= 1
        if numero >= 1 and fuente.linea(numero).lstrip().startswith('#'):
            continue        # el comentario pegado a la definicion es parte de ella
        if blancas != esperadas:
            out.append((inicio, '{!r} tiene {} linea(s) en blanco arriba y pide {}'
                        .format(getattr(nodo, 'name', '?'), blancas, esperadas)))
    return out


def check_codificacion(fuente, opts):
    """PEP 8 "Source File Encoding": UTF-8, y sin repetir la declaracion.

    Que decodifique lo comprueba `Fuente` al leerlo —si no, ninguna regla puede
    medir nada y sale exit 2—. Lo que queda para esta regla es la cookie: en
    Python 3 UTF-8 es el valor por omision, asi que declararlo es ruido.
    """
    out = []
    for numero in (1, 2):
        m = COOKIE.search(fuente.linea(numero))
        if m:
            out.append((numero, 'declara la codificacion ({}) y UTF-8 ya es el valor '
                                'por omision'.format(m.group(1))))
    return out


def check_imports(fuente, opts):
    """PEP 8 "Imports": uno por linea, sin comodines, y arriba de todo.

    No mide el orden de los grupos —estandar, terceros, local—: saber que
    paquete es de terceros pide el manifiesto, que no esta en el archivo. Es el
    mismo dato que `entorno_checks` obliga a declarar, y prometerlo aca seria
    medir con una lista adivinada.
    """
    out = []
    for nodo in ast.walk(fuente.arbol):
        if isinstance(nodo, ast.Import) and len(nodo.names) > 1:
            out.append((nodo.lineno, 'importa {} modulos en una linea: uno por linea'
                        .format(len(nodo.names))))
        if isinstance(nodo, ast.ImportFrom):
            if any(a.name == '*' for a in nodo.names):
                out.append((nodo.lineno, 'import con comodin de {!r}: borra que '
                                         'nombres entran al espacio de nombres'
                            .format(nodo.module or '.')))

    visto_codigo = None
    for nodo in fuente.arbol.body:
        if isinstance(nodo, (ast.Import, ast.ImportFrom)):
            if visto_codigo is not None:
                out.append((nodo.lineno, 'import despues de codigo (linea {}): los '
                                         'imports van arriba'.format(visto_codigo)))
        elif isinstance(nodo, ast.Expr) and isinstance(nodo.value, ast.Constant):
            continue        # docstring
        elif isinstance(nodo, ast.Assign) and all(
                isinstance(t, ast.Name) and t.id.startswith('__')
                for t in nodo.targets):
            continue        # dunder de modulo
        elif visto_codigo is None:
            visto_codigo = nodo.lineno
    return out


def check_dunder(fuente, opts):
    """PEP 8 "Module Level Dunder Names": despues del docstring y antes de los imports.

    `from __future__` es la excepcion que el propio documento nombra: tiene que
    ir antes de todo lo demas.
    """
    out = []
    primer_import = None
    for nodo in fuente.arbol.body:
        if isinstance(nodo, (ast.Import, ast.ImportFrom)):
            if isinstance(nodo, ast.ImportFrom) and nodo.module == '__future__':
                continue
            if primer_import is None:
                primer_import = nodo.lineno
        for linea, nombre, _valor in _asignaciones_de_modulo(ast.Module(
                body=[nodo], type_ignores=[])):
            if not (nombre.startswith('__') and nombre.endswith('__')):
                continue
            if primer_import is not None and linea > primer_import:
                out.append((linea, '{} va despues del primer import (linea {})'
                            .format(nombre, primer_import)))
    return out


# ---------------------------------------------------------------------------
# Espacios, comillas y comas
# ---------------------------------------------------------------------------

def check_comillas(fuente, opts):
    """PEP 8 "String Quotes": usar la otra comilla en vez de escapar.

    El documento no elige entre simples y dobles —dice que se elija una y se
    respete— pero si da una regla decidible: cuando la cadena contiene una
    comilla, se usa la otra para no llenar de barras.
    """
    out = []
    for t in fuente.tokens:
        if t.type != token_mod.STRING:
            continue
        texto = t.string
        prefijo = texto[:len(texto) - len(texto.lstrip('rRbBuUfF'))]
        cuerpo = texto[len(prefijo):]
        if cuerpo.startswith(('"""', "'''")):
            continue
        if 'r' in prefijo.lower():
            continue
        delimitador, contenido = cuerpo[0], cuerpo[1:-1]
        otra = '"' if delimitador == "'" else "'"
        if '\\' + delimitador in contenido and otra not in contenido:
            out.append((t.start[0], 'escapa {} pudiendo delimitar con {}'
                        .format(delimitador, otra)))
    return out


def _profundidad(tokens):
    """[(token, profundidad de parentesis antes del token)]."""
    salida, nivel = [], 0
    for t in tokens:
        if t.type == token_mod.OP and t.string in CIERRA:
            nivel -= 1
        salida.append((t, nivel))
        if t.type == token_mod.OP and t.string in ABRE:
            nivel += 1
    return salida


def check_espacios(fuente, opts):
    """PEP 8 "Pet Peeves": espacios sobrantes dentro de delimitadores y antes de coma.

    Se compara la posicion de cada token con la del anterior en la misma linea,
    que es lo unico que dice de verdad si habia un espacio. Sobre el texto crudo
    haria falta distinguir antes que es codigo y que es una cadena, o sea
    tokenizar igual.
    """
    out = []
    anterior = None
    for t in fuente.significativos():
        if t.type == token_mod.COMMENT:
            anterior = t
            continue
        if anterior is not None and anterior.end[0] == t.start[0]:
            hueco = t.start[1] - anterior.end[1]
            if anterior.string in ABRE and hueco > 0:
                out.append((t.start[0], 'espacio despues de {!r}'.format(anterior.string)))
            elif t.string in CIERRA and hueco > 0:
                out.append((t.start[0], 'espacio antes de {!r}'.format(t.string)))
            elif t.string in (',', ';') and hueco > 0:
                out.append((t.start[0], 'espacio antes de {!r}'.format(t.string)))
        anterior = t
    return out


def check_operadores(fuente, opts):
    """PEP 8 "Other Recommendations": el `=` con espacios o sin ellos, segun donde este.

    Un `=` de asignacion lleva un espacio a cada lado; el `=` de un argumento
    con nombre no lleva ninguno. Es la unica regla de este documento donde el
    mismo caracter pide dos cosas opuestas segun el contexto, y por eso hace
    falta la profundidad de parentesis.
    """
    out = []
    anterior = None
    for t, nivel in _profundidad(fuente.significativos()):
        if t.type == token_mod.OP and t.string == '=' and anterior is not None:
            antes = t.start[1] - anterior.end[1]
            if nivel > 0:
                if antes > 0:
                    out.append((t.start[0], 'espacio alrededor del = de un argumento '
                                            'con nombre'))
            elif antes == 0:
                out.append((t.start[0], 'falta el espacio alrededor del = de una '
                                        'asignacion'))
        if t.type != token_mod.COMMENT:
            anterior = t
    return out


def check_comafinal(fuente, opts):
    """PEP 8 "When to Use Trailing Commas": coma final si el cierre va en su linea.

    El documento lo pide para las listas pensadas para crecer, que es
    exactamente la forma que tiene un literal cuyo delimitador de cierre esta
    solo en su linea. Un literal vacio no pide nada: no hay elementos.
    """
    out = []
    pila = []
    anterior = None
    for t in fuente.significativos():
        if t.type == token_mod.COMMENT:
            continue
        if t.type == token_mod.OP and t.string in ABRE:
            pila.append((t.string, t.start[0]))
        elif t.type == token_mod.OP and t.string in CIERRA:
            if not pila:
                continue
            _apertura, linea_apertura = pila.pop()
            primero = fuente.linea(t.start[0]).strip().startswith(t.string)
            if primero and linea_apertura != t.start[0] and anterior is not None:
                if anterior.string not in (',',) + ABRE:
                    out.append((t.start[0], 'el {!r} cierra en su propia linea y falta '
                                            'la coma final'.format(t.string)))
        anterior = t
    return out


# ---------------------------------------------------------------------------
# Comentarios y docstrings
# ---------------------------------------------------------------------------

def check_bloque(fuente, opts):
    """PEP 8 "Block Comments": empiezan con `# ` y se sangran como el codigo.

    Un comentario de bloque es el que ocupa su linea. El `#!` de la primera
    linea no cuenta: es la linea de interprete, no un comentario del codigo.
    """
    out = []
    for t in fuente.tokens:
        if t.type != token_mod.COMMENT:
            continue
        if not fuente.linea(t.start[0]).strip().startswith('#'):
            continue        # es un comentario en linea, lo mide otra regla
        if t.start[0] == 1 and t.string.startswith('#!'):
            continue
        if t.string.startswith('#!') or t.string.rstrip() == '#':
            continue
        if not t.string.startswith('# '):
            out.append((t.start[0], 'comentario de bloque sin espacio despues del #'))
    return out


def check_enlinea(fuente, opts):
    """PEP 8 "Inline Comments": al menos dos espacios antes del `#`.

    Menos de dos y el comentario se lee pegado al codigo. Es una de las pocas
    reglas del documento con un numero, y por eso se puede medir sin discutir.
    """
    out = []
    for t in fuente.tokens:
        if t.type != token_mod.COMMENT:
            continue
        texto = fuente.linea(t.start[0])
        if texto.strip().startswith('#'):
            continue        # es de bloque
        if t.start[1] - len(texto[:t.start[1]].rstrip()) < 2:
            out.append((t.start[0], 'comentario en linea con menos de dos espacios '
                                    'antes del #'))
        elif not t.string.startswith('# '):
            out.append((t.start[0], 'comentario en linea sin espacio despues del #'))
    return out


def check_docstring(fuente, opts):
    """PEP 8 "Documentation Strings": toda API publica tiene docstring.

    Publica quiere decir que su nombre no empieza con guion bajo, que es lo
    unico decidible leyendo el archivo. Que el docstring diga algo util es otra
    cosa y no la mide nadie.
    """
    out = []
    if ast.get_docstring(fuente.arbol) is None:
        out.append((1, 'el modulo no tiene docstring'))
    for nodo in list(_defs(fuente.arbol)) + list(_clases(fuente.arbol)):
        if nodo.name.startswith('_'):
            continue
        if ast.get_docstring(nodo) is None:
            out.append((_primera_linea(nodo),
                        '{!r} es publica y no tiene docstring'.format(nodo.name)))
    return out


# ---------------------------------------------------------------------------
# Nombres
# ---------------------------------------------------------------------------

def _identificadores(arbol):
    """(linea, nombre) de todo identificador que el archivo declara."""
    for nodo in ast.walk(arbol):
        if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            yield nodo.lineno, nodo.name
            for arg in list(getattr(nodo, 'args', ast.arguments(
                    posonlyargs=[], args=[], kwonlyargs=[], kw_defaults=[],
                    defaults=[])).args if hasattr(nodo, 'args') else []):
                yield arg.lineno, arg.arg
        elif isinstance(nodo, ast.Name) and isinstance(nodo.ctx, ast.Store):
            yield nodo.lineno, nodo.id
        elif isinstance(nodo, ast.arg):
            yield nodo.lineno, nodo.arg


def check_ambiguos(fuente, opts):
    """PEP 8 "Names to Avoid": nunca `l`, `O` ni `I` de un solo caracter.

    En muchas tipografias son indistinguibles de uno y de cero. Es la regla mas
    facil de medir del documento y la que menos discusion admite: el umbral es
    cero y la lista la da el autor.
    """
    return [(linea, 'identificador {!r}: se confunde con un digito'.format(nombre))
            for linea, nombre in _identificadores(fuente.arbol)
            if nombre in AMBIGUOS]


def check_ascii(fuente, opts):
    """PEP 8 "ASCII Compatibility": los identificadores no salen de ASCII."""
    out = []
    for linea, nombre in _identificadores(fuente.arbol):
        if not nombre.isascii():
            out.append((linea, 'identificador {!r} fuera de ASCII'.format(nombre)))
    return out


def check_modulo(fuente, opts):
    """PEP 8 "Package and Module Names": minusculas, guiones bajos si ayudan.

    Mide el nombre del archivo, que es el nombre del modulo. Un guion, una
    mayuscula o un punto de mas hacen que no se pueda importar o que se importe
    distinto en dos sistemas de archivos.
    """
    nombre = os.path.splitext(os.path.basename(fuente.ruta))[0]
    if nombre == '__init__' or MODULO.match(nombre):
        return []
    return [(1, 'el modulo se llama {!r}: va en minusculas y sin guiones'
             .format(nombre))]


def check_clase(fuente, opts):
    """PEP 8 "Class Names": CapWords."""
    return [(c.lineno, 'la clase {!r} no esta en CapWords'.format(c.name))
            for c in _clases(fuente.arbol) if not CAPWORDS.match(c.name)]


def check_tipovar(fuente, opts):
    """PEP 8 "Type Variable Names": CapWords, con sufijo cuando hay varianza.

    `_co` para covariante y `_contra` para contravariante. El propio documento
    da los dos sufijos, asi que la regla no inventa la convencion: la lee.
    """
    out = []
    for linea, nombre, valor in _asignaciones_de_modulo(fuente.arbol):
        if not isinstance(valor, ast.Call):
            continue
        llamado = valor.func.id if isinstance(valor.func, ast.Name) else \
            getattr(valor.func, 'attr', '')
        if llamado != 'TypeVar':
            continue
        varianza = {kw.arg for kw in valor.keywords
                    if isinstance(kw.value, ast.Constant) and kw.value.value is True}
        if 'covariant' in varianza and not nombre.endswith('_co'):
            out.append((linea, '{!r} es covariante y no termina en _co'.format(nombre)))
        elif 'contravariant' in varianza and not nombre.endswith('_contra'):
            out.append((linea, '{!r} es contravariante y no termina en _contra'
                        .format(nombre)))
        elif not varianza and not CAPWORDS.match(nombre):
            out.append((linea, 'la variable de tipo {!r} no esta en CapWords'
                        .format(nombre)))
    return out


def check_excepcion(fuente, opts):
    """PEP 8 "Exception Names": CapWords siempre, sufijo Error si es un error.

    El documento condiciona el sufijo: *"deberia usarse el sufijo Error **si la
    excepcion es de verdad un error**"*. Esa es una clausula de juicio, del
    mismo tipo que las que dejan 75 criterios de WCAG en pila B, y una regla que
    la ignorara marcaria en rojo toda excepcion de control de flujo.

    Asi que la regla se parte en lo decidible y lo condicionado:

      - **CapWords**: siempre, porque una excepcion es una clase.
      - **sufijo Error**: solo cuando la clase **ya declaro que es un error**
        heredando de algo terminado en `Error`. Ahi no queda juicio que hacer,
        lo hizo el autor al elegir la base.

    Lo destapo correr la regla contra este repositorio: marcaba en rojo las diez
    `NoVerificable`, que heredan de `Exception` y no son errores sino la manera
    de decir "no puedo saber".
    """
    out = []
    for clase in _clases(fuente.arbol):
        bases = [b.id if isinstance(b, ast.Name) else getattr(b, 'attr', '')
                 for b in clase.bases]
        if not any(b.endswith(('Error', 'Exception', 'Warning')) for b in bases):
            continue
        if not CAPWORDS.match(clase.name):
            out.append((clase.lineno, 'la excepcion {!r} no esta en CapWords'
                        .format(clase.name)))
        elif any(b.endswith('Error') for b in bases) and                 not clase.name.endswith('Error'):
            out.append((clase.lineno, 'la excepcion {!r} hereda de un Error y no '
                                      'termina en Error'.format(clase.name)))
    return out


def check_global(fuente, opts):
    """PEP 8 "Global Variable Names": la misma convencion que las funciones.

    Alcanza a las globales cuyo valor NO es un literal; las que si lo son son
    constantes y las mide `constante`. Partirlo asi es lo unico que evita que
    las dos reglas se contradigan sobre el mismo nombre.
    """
    out = []
    for linea, nombre, valor in _asignaciones_de_modulo(fuente.arbol):
        if _es_literal(valor):
            continue
        if nombre.startswith('__') and nombre.endswith('__'):
            continue
        if SNAKE.match(nombre) or MAYUSCULAS.match(nombre):
            continue
        out.append((linea, 'la global {!r} no esta en minusculas con guion bajo'
                    .format(nombre)))
    return out


def check_funcion(fuente, opts):
    """PEP 8 "Function and Variable Names": minusculas con guion bajo."""
    out = []
    metodos = {id(m) for _c, m in _metodos(fuente.arbol)}
    for nodo in _defs(fuente.arbol):
        if id(nodo) in metodos:
            continue        # los metodos los mide `metodo`
        if not SNAKE.match(nodo.name):
            out.append((nodo.lineno, 'la funcion {!r} no esta en minusculas con '
                                     'guion bajo'.format(nodo.name)))
    return out


def check_primerarg(fuente, opts):
    """PEP 8 "Function and Method Arguments": `self` en instancia, `cls` en clase.

    Los estaticos quedan afuera porque no reciben ni uno ni otro, y esa es
    justamente la diferencia que el decorador declara.
    """
    out = []
    for _clase, metodo in _metodos(fuente.arbol):
        if _decorado(metodo, ('staticmethod',)):
            continue
        esperado = 'cls' if _decorado(metodo, ('classmethod',)) else 'self'
        argumentos = metodo.args.posonlyargs + metodo.args.args
        if not argumentos:
            out.append((metodo.lineno, '{!r} no recibe {}'.format(metodo.name, esperado)))
        elif argumentos[0].arg != esperado:
            out.append((metodo.lineno, '{!r} recibe {!r} y deberia recibir {!r}'
                        .format(metodo.name, argumentos[0].arg, esperado)))
    return out


def check_metodo(fuente, opts):
    """PEP 8 "Method Names and Instance Variables": minusculas con guion bajo.

    Cubre los metodos y los atributos que se asignan sobre `self`, que son las
    dos cosas que la seccion nombra.
    """
    out = []
    for _clase, metodo in _metodos(fuente.arbol):
        if not SNAKE.match(metodo.name):
            out.append((metodo.lineno, 'el metodo {!r} no esta en minusculas con '
                                       'guion bajo'.format(metodo.name)))
    for nodo in ast.walk(fuente.arbol):
        if not isinstance(nodo, ast.Attribute) or not isinstance(nodo.ctx, ast.Store):
            continue
        if isinstance(nodo.value, ast.Name) and nodo.value.id == 'self' \
                and not SNAKE.match(nodo.attr):
            out.append((nodo.lineno, 'el atributo {!r} no esta en minusculas con '
                                     'guion bajo'.format(nodo.attr)))
    return out


def check_constante(fuente, opts):
    """PEP 8 "Constants": mayusculas con guion bajo, en el nivel del modulo.

    Alcanza a las asignaciones de modulo cuyo valor es un literal, que es lo
    unico que se puede llamar constante leyendo el archivo. Lo demas lo mide
    `global`.
    """
    out = []
    for linea, nombre, valor in _asignaciones_de_modulo(fuente.arbol):
        if not _es_literal(valor):
            continue
        if nombre.startswith('__') and nombre.endswith('__'):
            continue
        if not MAYUSCULAS.match(nombre):
            out.append((linea, 'la constante {!r} no esta en mayusculas'.format(nombre)))
    return out


def check_publica(fuente, opts):
    """PEP 8 "Public and Internal Interfaces": la superficie publica se declara.

    Un modulo con nombres publicos declara `__all__`. Es lo mismo que exige
    `check_g9` antes de hablar de codigo muerto, y por el mismo motivo: sin
    saber que es publico no se puede decir ni que sobra ni que se expone.
    """
    publicos = [n.name for n in list(_defs(fuente.arbol)) + list(_clases(fuente.arbol))
                if not n.name.startswith('_')]
    if not publicos:
        return []
    declarado = any(nombre == '__all__'
                    for _l, nombre, _v in _asignaciones_de_modulo(fuente.arbol))
    if declarado:
        return []
    return [(1, 'el modulo expone {} nombre(s) publico(s) y no declara __all__'
             .format(len(publicos)))]


# ---------------------------------------------------------------------------
# Anotaciones
# ---------------------------------------------------------------------------

def _espacios_de_anotacion(fuente, dentro_de_def):
    """Hallazgos de espaciado en `->` y en los dos puntos de anotacion."""
    out = []
    anterior = None
    for t, nivel in _profundidad(fuente.significativos()):
        if t.type == token_mod.OP and t.string == '->' and anterior is not None:
            if t.start[1] - anterior.end[1] != 1:
                out.append((t.start[0], 'falta el espacio antes de ->'))
        if t.type != token_mod.COMMENT:
            anterior = t
    return out if dentro_de_def else []


def check_anotafuncion(fuente, opts):
    """PEP 8 "Function Annotations": un espacio a cada lado de `->`.

    Y los dos puntos de un argumento anotado siguen la regla de siempre: sin
    espacio antes, uno despues.
    """
    out = list(_espacios_de_anotacion(fuente, True))
    for nodo in _defs(fuente.arbol):
        for arg in nodo.args.posonlyargs + nodo.args.args + nodo.args.kwonlyargs:
            if arg.annotation is None:
                continue
            texto = fuente.linea(arg.lineno)
            trozo = texto[arg.col_offset:]
            m = re.match(re.escape(arg.arg) + r'(\s*):(\s*)', trozo)
            if m and (m.group(1) or m.group(2) != ' '):
                out.append((arg.lineno, 'la anotacion de {!r} no lleva "nombre: tipo"'
                            .format(arg.arg)))
    return out


def check_anotavariable(fuente, opts):
    """PEP 8 "Variable Annotations": sin espacio antes de los dos puntos, uno despues."""
    out = []
    for nodo in ast.walk(fuente.arbol):
        if not isinstance(nodo, ast.AnnAssign) or not isinstance(nodo.target, ast.Name):
            continue
        texto = fuente.linea(nodo.lineno)
        trozo = texto[nodo.col_offset:]
        m = re.match(re.escape(nodo.target.id) + r'(\s*):(\s*)', trozo)
        if m and (m.group(1) or m.group(2) != ' '):
            out.append((nodo.lineno, 'la anotacion de {!r} no lleva "nombre: tipo"'
                        .format(nodo.target.id)))
    return out


RULES = {
    'ambiguos': (check_ambiguos, 'Nombres a evitar: ni l, ni O, ni I'),
    'anotafuncion': (check_anotafuncion, 'Anotaciones de funcion: espaciado'),
    'anotavariable': (check_anotavariable, 'Anotaciones de variable: espaciado'),
    'ascii': (check_ascii, 'ASCII: los identificadores no salen de ASCII'),
    'blancos': (check_blancos, 'Lineas en blanco: dos arriba, una entre metodos'),
    'bloque': (check_bloque, 'Comentarios de bloque: empiezan con "# "'),
    'clase': (check_clase, 'Nombres de clase: CapWords'),
    'codificacion': (check_codificacion, 'Codificacion: UTF-8 sin declararlo'),
    'comafinal': (check_comafinal, 'Coma final: si el cierre va en su linea'),
    'comillas': (check_comillas, 'Comillas: usar la otra en vez de escapar'),
    'constante': (check_constante, 'Constantes: mayusculas con guion bajo'),
    'docstring': (check_docstring, 'Docstrings: toda API publica tiene uno'),
    'dunder': (check_dunder, 'Dunder de modulo: antes de los imports'),
    'enlinea': (check_enlinea, 'Comentarios en linea: dos espacios antes del #'),
    'espacios': (check_espacios, 'Espacios sobrantes: en delimitadores y comas'),
    'excepcion': (check_excepcion, 'Nombres de excepcion: terminan en Error'),
    'funcion': (check_funcion, 'Nombres de funcion: minusculas con guion bajo'),
    'global': (check_global, 'Nombres de globales: minusculas con guion bajo'),
    'imports': (check_imports, 'Imports: uno por linea, sin comodines, arriba'),
    'metodo': (check_metodo, 'Nombres de metodo y atributo: minusculas'),
    'modulo': (check_modulo, 'Nombres de modulo: minusculas sin guiones'),
    'operador': (check_operador, 'Corte de linea: antes del operador binario'),
    'operadores': (check_operadores, 'Espacios: el = segun donde este'),
    'primerarg': (check_primerarg, 'Primer argumento: self o cls'),
    'publica': (check_publica, 'Superficie publica: el modulo declara __all__'),
    'sangria': (check_sangria, 'Sangria: cuatro espacios por nivel'),
    'tipovar': (check_tipovar, 'Variables de tipo: CapWords y sufijo de varianza'),
}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--rule')
    parser.add_argument('--list', action='store_true')
    parser.add_argument('files', nargs='*')
    args = parser.parse_args(argv)

    if args.list:
        for nombre in sorted(RULES):
            print('{:14} {}'.format(nombre, RULES[nombre][1]))
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
            for linea, detalle in func(Fuente(ruta), args):
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
