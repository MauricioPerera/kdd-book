"""Los instrumentos de PEP 8 contra archivos rojos y verdes.

Son 27 reglas, asi que el grueso va en una tabla: cada regla con el fragmento
minimo que la incumple y el que la cumple. La tabla no es un atajo — es lo que
hace que agregar una regla sin caso de prueba falle, porque
`test_toda_regla_tiene_su_par` compara la tabla contra `RULES` y no contra una
lista escrita a mano.

Las reglas con una sutileza que la tabla no muestra —el `=` que pide cosas
opuestas segun el contexto, el comentario dentro de un string, la sangria de
continuacion— traen ademas su prueba propia.
"""

import argparse
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..',
                                'instruments'))

import pep8_checks as P  # noqa: E402


VERDE = '"""Modulo de prueba."""\n\n__all__ = []\n\nimport os\n\nCONSTANTE = 1\n'

# regla -> (fragmento rojo, fragmento verde)
CASOS = {
    'sangria': ('def f():\n      return 1\n', 'def f():\n    return 1\n'),
    'operador': ('x = (1 +\n     2)\n', 'x = (1\n     + 2)\n'),
    'blancos': ('def a():\n    pass\ndef b():\n    pass\n',
                'def a():\n    pass\n\n\ndef b():\n    pass\n'),
    'codificacion': ('# -*- coding: utf-8 -*-\nx = 1\n', 'x = 1\n'),
    'imports': ('from os import *\n', 'import os\n'),
    'dunder': ('import os\n__version__ = "1"\n', '__version__ = "1"\nimport os\n'),
    'comillas': ("x = 'no \\'va\\''\n", 'x = "no \'va\'"\n'),
    'espacios': ('f( 1 )\n', 'f(1)\n'),
    'operadores': ('x=1\n', 'x = 1\n'),
    'comafinal': ('X = [\n    1,\n    2\n]\n', 'X = [\n    1,\n    2,\n]\n'),
    'bloque': ('#un comentario\nx = 1\n', '# un comentario\nx = 1\n'),
    'enlinea': ('x = 1 # tarde\n', 'x = 1  # tarde\n'),
    'docstring': ('def publica():\n    return 1\n',
                  '"""Modulo."""\n\n\ndef publica():\n    """Hace algo."""\n    return 1\n'),
    'ambiguos': ('l = 1\n', 'largo = 1\n'),
    'ascii': ('anio = 1\nsenal = 2\ncafe\u0301 = 3\n', 'anio = 1\nsenal = 2\n'),
    'modulo': (None, None),          # depende del nombre de archivo, prueba propia
    'clase': ('class mi_clase:\n    pass\n', 'class MiClase:\n    pass\n'),
    'tipovar': ('from typing import TypeVar\nT = TypeVar("T", covariant=True)\n',
                'from typing import TypeVar\nT_co = TypeVar("T_co", covariant=True)\n'),
    'excepcion': ('class Fallo(ValueError):\n    pass\n',
                  'class FalloError(ValueError):\n    pass\n'),
    'global': ('import os\nMiRegistro = os.environ\n', 'import os\nregistro = os.environ\n'),
    'funcion': ('def HacerAlgo():\n    pass\n', 'def hacer_algo():\n    pass\n'),
    'primerarg': ('class A:\n    def m(x):\n        pass\n',
                  'class A:\n    def m(self):\n        pass\n'),
    'metodo': ('class A:\n    def HacerAlgo(self):\n        pass\n',
               'class A:\n    def hacer_algo(self):\n        pass\n'),
    'constante': ('limite = 10\n', 'LIMITE = 10\n'),
    'publica': ('def publica():\n    pass\n', '__all__ = ["publica"]\n\n\ndef publica():\n    pass\n'),
    'anotafuncion': ('def f(a:int):\n    pass\n', 'def f(a: int):\n    pass\n'),
    'anotavariable': ('x:int = 1\n', 'x: int = 1\n'),
}


class Pep8ChecksTest(unittest.TestCase):

    def setUp(self):
        self.raiz = tempfile.mkdtemp(prefix='kddbook-pep8-')
        self.addCleanup(shutil.rmtree, self.raiz, True)

    def _fuente(self, codigo, nombre='modulo.py'):
        ruta = os.path.join(self.raiz, nombre)
        with open(ruta, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(codigo)
        return P.Fuente(ruta)

    def _correr(self, regla, codigo, nombre='modulo.py'):
        return P.RULES[regla][0](self._fuente(codigo, nombre), argparse.Namespace())

    # ------------------------------------------------------------ estructura
    def test_toda_regla_tiene_su_par(self):
        self.assertEqual(set(P.RULES) - set(CASOS), set(),
                         'hay reglas de PEP 8 sin caso de prueba')
        self.assertEqual(set(CASOS) - set(P.RULES), set(),
                         'hay casos de prueba para reglas que no existen')

    def test_todas_las_funciones_check_estan_registradas(self):
        definidas = {n[len('check_'):] for n in dir(P) if n.startswith('check_')}
        self.assertEqual(definidas - set(P.RULES), set(),
                         'hay checks escritos que el instrumento no puede ejecutar')

    def test_cada_regla_detecta_su_rojo(self):
        for regla, (rojo, _verde) in sorted(CASOS.items()):
            if rojo is None:
                continue
            with self.subTest(regla=regla):
                self.assertTrue(self._correr(regla, rojo),
                                'la regla no detecta su propio caso rojo')

    def test_cada_regla_acepta_su_verde(self):
        for regla, (_rojo, verde) in sorted(CASOS.items()):
            if verde is None:
                continue
            with self.subTest(regla=regla):
                self.assertEqual(self._correr(regla, verde), [],
                                 'la regla marca su propio caso verde')

    def test_ninguna_regla_se_queja_de_un_archivo_impecable(self):
        """Un instrumento que marca codigo correcto es peor que no tenerlo."""
        for regla in sorted(P.RULES):
            if regla in ('modulo',):
                continue
            with self.subTest(regla=regla):
                self.assertEqual(self._correr(regla, VERDE), [])

    # ------------------------------------------------------------- sutilezas
    def test_operadores_pide_lo_contrario_segun_el_contexto(self):
        """El mismo `=` con espacios en una asignacion y sin ellos en un argumento."""
        self.assertTrue(self._correr('operadores', 'f(a = 1)\n'),
                        'no detecto el espacio alrededor del = de un argumento')
        self.assertEqual(self._correr('operadores', 'f(a=1)\n'), [])
        self.assertEqual(self._correr('operadores', 'x = f(a=1)\n'), [])

    def test_bloque_no_confunde_un_numeral_dentro_de_un_string(self):
        """Por esto la familia usa tokenize y no expresiones regulares."""
        self.assertEqual(self._correr('bloque', 'x = "#sin espacio"\n'), [],
                         'tomo por comentario un numeral que esta dentro de un string')

    def test_enlinea_no_confunde_un_numeral_dentro_de_un_string(self):
        self.assertEqual(self._correr('enlinea', 'x = "a # b"\n'), [])

    def test_sangria_no_mide_las_lineas_de_continuacion(self):
        """Se alinean con el delimitador, no con un multiplo de cuatro."""
        self.assertEqual(self._correr('sangria', 'x = f(1,\n      2)\n'), [])

    def test_bloque_acepta_la_linea_de_interprete(self):
        self.assertEqual(self._correr('bloque', '#!/usr/bin/env python3\nx = 1\n'), [])

    def test_comafinal_no_pide_nada_en_una_sola_linea(self):
        self.assertEqual(self._correr('comafinal', 'X = [1, 2]\n'), [])

    def test_comafinal_no_pide_nada_en_un_literal_vacio(self):
        self.assertEqual(self._correr('comafinal', 'X = [\n]\n'), [])

    def test_comillas_no_marca_la_cadena_que_necesita_las_dos(self):
        """Si el contenido trae las dos comillas, escapar es inevitable."""
        self.assertEqual(self._correr('comillas', 'x = \'dice "hola" y \\\'chau\\\'\'\n'), [])

    def test_dunder_acepta_el_import_de_future(self):
        codigo = 'from __future__ import annotations\n__version__ = "1"\nimport os\n'
        self.assertEqual(self._correr('dunder', codigo), [])

    def test_primerarg_no_le_pide_self_a_un_estatico(self):
        codigo = 'class A:\n    @staticmethod\n    def m(x):\n        pass\n'
        self.assertEqual(self._correr('primerarg', codigo), [])

    def test_primerarg_le_pide_cls_a_un_metodo_de_clase(self):
        codigo = 'class A:\n    @classmethod\n    def m(self):\n        pass\n'
        self.assertTrue(self._correr('primerarg', codigo))

    def test_global_y_constante_no_se_contradicen(self):
        """Se reparten por el valor: literal es constante, lo demas es global.

        Sin ese reparto las dos reglas opinarian sobre el mismo nombre y una
        pediria mayusculas mientras la otra pide minusculas.
        """
        literal = 'LIMITE = 10\n'
        self.assertEqual(self._correr('constante', literal), [])
        self.assertEqual(self._correr('global', literal), [])
        calculado = 'import os\nregistro = os.environ\n'
        self.assertEqual(self._correr('constante', calculado), [])
        self.assertEqual(self._correr('global', calculado), [])

    def test_docstring_no_le_pide_nada_a_lo_privado(self):
        codigo = '"""Modulo."""\n\n\ndef _interna():\n    pass\n'
        self.assertEqual(self._correr('docstring', codigo), [])

    def test_publica_no_le_pide_nada_a_un_modulo_sin_api(self):
        self.assertEqual(self._correr('publica', '"""M."""\n\n\ndef _x():\n    pass\n'), [])

    def test_modulo_mide_el_nombre_del_archivo(self):
        self.assertEqual(self._correr('modulo', 'x = 1\n', 'mi_modulo.py'), [])
        self.assertTrue(self._correr('modulo', 'x = 1\n', 'MiModulo.py'))
        self.assertTrue(self._correr('modulo', 'x = 1\n', 'mi-modulo.py'))

    def test_blancos_no_le_pide_nada_al_primer_metodo_de_una_clase(self):
        codigo = 'class A:\n    def m(self):\n        pass\n'
        self.assertEqual(self._correr('blancos', codigo), [])

    def test_blancos_pide_una_sola_entre_metodos(self):
        pegados = 'class A:\n    def m(self):\n        pass\n    def n(self):\n        pass\n'
        self.assertTrue(self._correr('blancos', pegados))
        separados = ('class A:\n    def m(self):\n        pass\n\n'
                     '    def n(self):\n        pass\n')
        self.assertEqual(self._correr('blancos', separados), [])

    def test_excepcion_solo_mira_lo_que_hereda_de_una_excepcion(self):
        self.assertEqual(self._correr('excepcion', 'class Fallo:\n    pass\n'), [],
                         'una clase cualquiera no es una excepcion')

    def test_excepcion_no_le_pide_error_a_lo_que_no_es_un_error(self):
        """El sufijo esta condicionado en el propio documento a que sea un error.

        Lo destapo correr la regla contra este repositorio: marcaba las diez
        `NoVerificable`, que heredan de Exception y significan "no puedo saber".
        """
        self.assertEqual(
            self._correr('excepcion', 'class NoVerificable(Exception):\n    pass\n'),
            [], 'le pidio el sufijo Error a una excepcion que no es un error')

    def test_excepcion_si_le_pide_error_a_lo_que_ya_declaro_serlo(self):
        """Heredar de un Error es el autor declarando que es un error."""
        self.assertTrue(self._correr('excepcion', 'class Fallo(ValueError):\n    pass\n'))

    def test_excepcion_exige_capwords_siempre(self):
        self.assertTrue(self._correr('excepcion',
                                     'class mi_fallo(Exception):\n    pass\n'))

    def test_blancos_no_le_pide_dos_a_una_funcion_anidada(self):
        """Las dos lineas son para el nivel superior, no para adentro.

        Lo destapo correr la regla contra este repositorio: marcaba un
        `_reemplazo` de tres lineas metido adentro de su unica llamadora, que es
        justo el caso donde separar seria peor.
        """
        codigo = ('def externa():\n    """Doc."""\n'
                  '    def _interna():\n        return 1\n    return _interna()\n')
        self.assertEqual(self._correr('blancos', codigo), [])

    # ------------------------------------------------------------ no medible
    def test_un_archivo_que_no_compila_no_se_mide(self):
        with self.assertRaises(P.NoVerificable):
            self._fuente('def f(\n')

    def test_un_archivo_que_no_decodifica_no_se_mide(self):
        ruta = os.path.join(self.raiz, 'raro.py')
        with open(ruta, 'wb') as fh:
            fh.write(b'x = "\xff\xfe"\n')
        with self.assertRaises(P.NoVerificable):
            P.Fuente(ruta)


if __name__ == '__main__':
    unittest.main()
