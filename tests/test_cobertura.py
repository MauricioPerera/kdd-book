"""Toda tecnica con instrumento tiene ejercicio, salvo excepciones declaradas.

Existe porque la cobertura se estaba comprobando a mano, y a mano no sobrevive
al proximo libro. Sin esta prueba, un instrumento nuevo sin ejercicio no lo
detecta nadie: los gates pasan igual, porque un contrato que no existe no falla.

Que las excepciones esten declaradas es la mitad del valor. Una lista de
pendientes que nadie mira se convierte en una lista de olvidados; una que el
test obliga a mantener exacta —falla tanto si sobra como si falta— es un
inventario.
"""

import glob
import re
import json
import os
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
LIBROS = ('codigo-limpio', 'scrum-xp', 'arquitectura-java', 'htmx',
          'doce-factores', 'wcag', 'pep8')

# Tecnicas con instrumento que a proposito NO tienen ejercicio, y por que.
#
# Las tres son de `git_checks`. Su instrumento funciona y esta probado contra
# repositorios reales, pero **no admiten la forma de ejercicio**: lo que hay que
# arreglar no es un archivo sino el historial. Integrar una rama, marcar una
# entrega o escribir el test antes que el codigo son operaciones de git, y
# `touch_only` cubre archivos, no commits.
#
# La tentacion seria darle al ejercicio un script que fabrique el historial y
# poner ESE script como target. Seria enseñar a fabricar un historial que se vea
# bien, que es lo contrario de la tecnica.
SIN_EJERCICIO = {
    ('git_checks.py', 'cadencia'): 'el arreglo es marcar una entrega, no editar un archivo',
    ('git_checks.py', 'repounico'): 'el arreglo es integrar una rama, no editar un archivo',
    ('git_checks.py', 'tddorden'): 'el arreglo es el orden de los commits, no el contenido de un archivo',
    ('git_checks.py', 'codebase'): 'el arreglo es poner el proyecto bajo control de versiones o sacar un repositorio anidado, no editar un archivo',
    ('git_checks.py', 'releaseid'): 'el arreglo es marcar el release, no editar un archivo',
}

# Instrumentos que SI admiten la forma de ejercicio y todavia no lo tienen.
#
# `SIN_EJERCICIO` dice "no se puede" y no se vacia nunca: describe un limite de
# la forma de contrato. Esto dice "no esta hecho" y se vacia trabajando.
# Mezclarlos convertiria el inventario en una lista donde lo imposible y lo
# pendiente se ven igual.
PENDIENTE = {
    ('pep8_checks.py', 'ambiguos'): (
        'el instrumento esta escrito y probado; falta el ejercicio'),
    ('pep8_checks.py', 'anotafuncion'): (
        'el instrumento esta escrito y probado; falta el ejercicio'),
    ('pep8_checks.py', 'anotavariable'): (
        'el instrumento esta escrito y probado; falta el ejercicio'),
    ('pep8_checks.py', 'ascii'): (
        'el instrumento esta escrito y probado; falta el ejercicio'),
    ('pep8_checks.py', 'blancos'): (
        'el instrumento esta escrito y probado; falta el ejercicio'),
    ('pep8_checks.py', 'bloque'): (
        'el instrumento esta escrito y probado; falta el ejercicio'),
    ('pep8_checks.py', 'clase'): (
        'el instrumento esta escrito y probado; falta el ejercicio'),
    ('pep8_checks.py', 'codificacion'): (
        'el instrumento esta escrito y probado; falta el ejercicio'),
    ('pep8_checks.py', 'comafinal'): (
        'el instrumento esta escrito y probado; falta el ejercicio'),
    ('pep8_checks.py', 'comillas'): (
        'el instrumento esta escrito y probado; falta el ejercicio'),
    ('pep8_checks.py', 'constante'): (
        'el instrumento esta escrito y probado; falta el ejercicio'),
    ('pep8_checks.py', 'docstring'): (
        'el instrumento esta escrito y probado; falta el ejercicio'),
    ('pep8_checks.py', 'dunder'): (
        'el instrumento esta escrito y probado; falta el ejercicio'),
    ('pep8_checks.py', 'enlinea'): (
        'el instrumento esta escrito y probado; falta el ejercicio'),
    ('pep8_checks.py', 'espacios'): (
        'el instrumento esta escrito y probado; falta el ejercicio'),
    ('pep8_checks.py', 'excepcion'): (
        'el instrumento esta escrito y probado; falta el ejercicio'),
    ('pep8_checks.py', 'funcion'): (
        'el instrumento esta escrito y probado; falta el ejercicio'),
    ('pep8_checks.py', 'global'): (
        'el instrumento esta escrito y probado; falta el ejercicio'),
    ('pep8_checks.py', 'imports'): (
        'el instrumento esta escrito y probado; falta el ejercicio'),
    ('pep8_checks.py', 'metodo'): (
        'el instrumento esta escrito y probado; falta el ejercicio'),
    ('pep8_checks.py', 'modulo'): (
        'el instrumento esta escrito y probado; falta el ejercicio'),
    ('pep8_checks.py', 'operador'): (
        'el instrumento esta escrito y probado; falta el ejercicio'),
    ('pep8_checks.py', 'operadores'): (
        'el instrumento esta escrito y probado; falta el ejercicio'),
    ('pep8_checks.py', 'primerarg'): (
        'el instrumento esta escrito y probado; falta el ejercicio'),
    ('pep8_checks.py', 'publica'): (
        'el instrumento esta escrito y probado; falta el ejercicio'),
    ('pep8_checks.py', 'sangria'): (
        'el instrumento esta escrito y probado; falta el ejercicio'),
    ('pep8_checks.py', 'tipovar'): (
        'el instrumento esta escrito y probado; falta el ejercicio'),
}


def _alias_de(script):
    """ALIASES del modulo del instrumento, si tiene."""
    import sys
    sys.path.insert(0, os.path.join(RAIZ, 'instruments'))
    if not script.endswith('.py'):
        return {}
    try:
        modulo = __import__(script[:-3])
    except ImportError:
        return {}
    return getattr(modulo, 'ALIASES', {})


def _regla(partes, script=''):
    """Regla canonica: los alias se resuelven a su destino.

    Hace falta porque un nodo puede declarar `--rule g15` y su ejercicio usar
    `--rule f3`: el libro define G15 igual que F3, asi que comparten
    instrumento. Comparar los nombres crudos los daria por distintos y
    reportaria como pendiente un ejercicio que ya existe.
    """
    if '--rule' not in partes:
        return ''
    regla = partes[partes.index('--rule') + 1]
    return _alias_de(script).get(regla, regla)


def _instrumentos_ejercitados():
    """(script, regla) de cada ejercicio, de cualquier libro."""
    out = set()
    for ruta in sorted(glob.glob(os.path.join(RAIZ, 'exercises', '*', '*', 'spec.json'))):
        with open(ruta, 'r', encoding='utf-8') as fh:
            instrumento = json.load(fh)['instrument']
        out.add((instrumento['script'],
                 _regla(instrumento.get('args', []), instrumento['script'])))
    return out


def _tecnicas_con_script():
    """(libro, nodo, script, regla) de cada tecnica cuyo instrumento existe."""
    out = []
    for libro in LIBROS:
        ruta = os.path.join(RAIZ, 'books', libro + '.json')
        with open(ruta, 'r', encoding='utf-8') as fh:
            spec = json.load(fh)
        for node in spec['nodes']:
            if node['pile'] != 'A' or node.get('verification') != 'instrumented':
                continue
            partes = node['instrument'].split()
            script = partes[0]
            if not script.endswith('.py'):
                continue
            if not os.path.isfile(os.path.join(RAIZ, 'instruments', script)):
                continue
            out.append((libro, node['id'], script, _regla(partes, script)))
    return out


class IdentidadTest(unittest.TestCase):
    """Los ids de nodo no pueden depender del idioma del libro.

    Existe por un defecto real. Los ids eran el codigo del autor pegado a un
    slug del titulo: `g36-evitar-desplazamientos-transitivos`. Con eso, el
    mismo nodo de la edicion inglesa habria sido
    `g36-avoid-transitive-navigation`, o sea otro nodo. Tres consecuencias, y
    ninguna la detectaba nadie porque cada grafo validaba perfecto por
    separado:

      - los enlaces entre libros dejan de resolver;
      - dos grafos del mismo libro en idiomas distintos no se fusionan, se
        duplican;
      - la memoria exportada no se puede juntar con la de otro.

    Ahora el id es solo el identificador del autor (`g36`, `142`, `08`) y el
    titulo es una etiqueta que cambia con la edicion.
    """

    # Codigo del autor: letras opcionales y numeros, con guion bajo entre
    # numerales. Nada de prosa.
    #
    # El guion entro con WCAG, cuyo identificador de autor es una numeracion
    # jerarquica: `1.4.13`. Ampliar la forma no afloja la invariante, porque la
    # invariante no es "el id es corto" sino **el id no depende del idioma**:
    # `sc1-4-13` es la numeracion del autor y es la misma en la traduccion al
    # castellano.
    #
    # Y sigue rechazando lo que existia para rechazar: el guion solo une
    # NUMERALES, asi que `g36-evitar-desplazamientos-transitivos` —el id con
    # prosa que motivo esta prueba— no matchea.
    ID_ESTABLE = re.compile(r'^[a-z]{0,4}\d{1,3}(?:-\d{1,3}){0,2}$')

    def test_los_ids_no_llevan_prosa(self):
        for libro in LIBROS:
            with open(os.path.join(RAIZ, 'books', libro + '.json'),
                      encoding='utf-8') as fh:
                nodes = json.load(fh)['nodes']
            for node in nodes:
                with self.subTest(libro=libro, nodo=node['id']):
                    self.assertRegex(
                        node['id'], self.ID_ESTABLE,
                        'el id lleva texto del titulo: cambiaria con la traduccion')

    def test_los_ids_no_dependen_del_titulo(self):
        """Comprobacion directa: cambiar el titulo no puede cambiar el id."""
        for libro in LIBROS:
            with open(os.path.join(RAIZ, 'books', libro + '.json'),
                      encoding='utf-8') as fh:
                nodes = json.load(fh)['nodes']
            for node in nodes:
                palabras = [p for p in re.split(r'[^a-z]+', node['title'].lower())
                            if len(p) > 3]
                with self.subTest(libro=libro, nodo=node['id']):
                    for palabra in palabras:
                        self.assertNotIn(
                            palabra, node['id'],
                            'el id contiene una palabra del titulo')

    def test_toda_tecnica_medible_tiene_nombre_canonico(self):
        """Sin alias, una tecnica solo se encuentra con las palabras del traductor.

        Se exige en pila A sin excepciones: son las que tienen instrumento y
        contrato, o sea justo las que un agente va a querer buscar. En pila B se
        completan las que tienen nombre reconocido, pero no se exige: hay
        subsecciones ("Funciones y responsabilidades", "Reglas del Juego") que
        no son tecnicas y no tienen nombre canonico, e inventarles uno seria
        meter ruido en la busqueda. Pila C son temas, tecnologias y pasos de
        tutorial: ahi el alias no aporta nada.
        """
        for libro in LIBROS:
            with open(os.path.join(RAIZ, 'books', libro + '.json'),
                      encoding='utf-8') as fh:
                nodes = json.load(fh)['nodes']
            for node in nodes:
                if node['pile'] != 'A':
                    continue
                with self.subTest(libro=libro, nodo=node['id']):
                    self.assertTrue(
                        node.get('alias'),
                        'tecnica medible sin nombre canonico: no se puede '
                        'encontrar desde otro idioma ni cruzar con otro libro')

    def test_los_enlaces_cruzados_usan_ids_estables(self):
        for libro in LIBROS:
            with open(os.path.join(RAIZ, 'books', libro + '.json'),
                      encoding='utf-8') as fh:
                nodes = json.load(fh)['nodes']
            for node in nodes:
                for destino in node.get('links', []):
                    objetivo = destino.split('/')[-1]
                    with self.subTest(origen=node['id'], destino=destino):
                        self.assertRegex(
                            objetivo, self.ID_ESTABLE,
                            'el enlace apunta a un id con prosa')


class CoberturaTest(unittest.TestCase):

    def test_toda_tecnica_con_instrumento_tiene_ejercicio(self):
        ejercitados = _instrumentos_ejercitados()
        sin_cubrir = {(script, regla)
                      for _libro, _nodo, script, regla in _tecnicas_con_script()
                      if (script, regla) not in ejercitados}
        self.assertEqual(
            sin_cubrir, set(SIN_EJERCICIO) | set(PENDIENTE),
            'la cobertura de ejercicios cambio: hay instrumentos sin ejercicio '
            'que no estan declarados ni en SIN_EJERCICIO ni en PENDIENTE, o '
            'declaraciones que ya no hacen falta')

    def test_cada_excepcion_declara_su_motivo(self):
        for clave, motivo in list(SIN_EJERCICIO.items()) + list(PENDIENTE.items()):
            self.assertTrue(motivo and len(motivo) > 20,
                            'la excepcion {} no explica por que'.format(clave))

    def test_lo_imposible_y_lo_pendiente_no_se_mezclan(self):
        """Un instrumento no puede estar en las dos listas a la vez.

        La distincion es el valor de la prueba: `SIN_EJERCICIO` no se vacia
        nunca porque describe un limite de la forma de contrato; `PENDIENTE` se
        vacia trabajando. Si un mismo instrumento cayera en las dos, dejaria de
        saberse cual es cual.
        """
        self.assertEqual(set(SIN_EJERCICIO) & set(PENDIENTE), set(),
                         'un instrumento esta declarado imposible y pendiente a la vez')

    def test_los_instrumentos_declarados_existen(self):
        """Un nodo que nombra un script inexistente promete lo que no tiene."""
        for libro in LIBROS:
            with open(os.path.join(RAIZ, 'books', libro + '.json'),
                      encoding='utf-8') as fh:
                spec = json.load(fh)
            for node in spec['nodes']:
                if node['pile'] != 'A':
                    continue
                script = node['instrument'].split()[0]
                if not script.endswith('.py'):
                    continue
                with self.subTest(libro=libro, nodo=node['id']):
                    self.assertTrue(
                        os.path.isfile(os.path.join(RAIZ, 'instruments', script)),
                        'el nodo nombra {} y ese script no existe'.format(script))

    def test_ninguna_regla_de_ejercicio_es_inventada(self):
        """Un ejercicio que apunta a una regla inexistente nunca esta en verde."""
        import sys
        sys.path.insert(0, os.path.join(RAIZ, 'instruments'))
        registros = {}
        # Estan los siete a proposito. Las tres familias nuevas —html, http,
        # plantillas— faltaban, y con eso sus ejercicios pasaban por esta prueba
        # sin que nadie comprobara que la regla que nombran existe.
        for modulo in ('checks', 'repo_checks', 'git_checks', 'arch_checks',
                       'mutation_checks', 'html_checks', 'http_checks',
                       'template_checks', 'entorno_checks', 'a11y_checks',
                       'pep8_checks'):
            registros[modulo + '.py'] = __import__(modulo)
        for script, regla in sorted(_instrumentos_ejercitados()):
            if not regla or script not in registros:
                continue
            modulo = registros[script]
            validas = set(modulo.RULES) | set(getattr(modulo, 'ALIASES', {}))
            with self.subTest(script=script, regla=regla):
                self.assertIn(regla, validas,
                              'un ejercicio usa una regla que el instrumento no tiene')


if __name__ == '__main__':
    unittest.main()
