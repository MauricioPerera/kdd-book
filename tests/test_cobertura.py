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
import json
import os
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
LIBROS = ('codigo-limpio', 'scrum-xp', 'arquitectura-java')

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


class CoberturaTest(unittest.TestCase):

    def test_toda_tecnica_con_instrumento_tiene_ejercicio(self):
        ejercitados = _instrumentos_ejercitados()
        sin_cubrir = {(script, regla)
                      for _libro, _nodo, script, regla in _tecnicas_con_script()
                      if (script, regla) not in ejercitados}
        self.assertEqual(
            sin_cubrir, set(SIN_EJERCICIO),
            'la cobertura de ejercicios cambio: hay instrumentos sin ejercicio '
            'que no estan declarados en SIN_EJERCICIO, o excepciones declaradas '
            'que ya no hacen falta')

    def test_cada_excepcion_declara_su_motivo(self):
        for clave, motivo in SIN_EJERCICIO.items():
            self.assertTrue(motivo and len(motivo) > 20,
                            'la excepcion {} no explica por que'.format(clave))

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
        for modulo in ('checks', 'repo_checks', 'git_checks', 'arch_checks',
                       'mutation_checks'):
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
