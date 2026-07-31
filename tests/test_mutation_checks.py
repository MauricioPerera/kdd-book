"""El instrumento de mutacion contra proyectos reales en temporales.

Este instrumento **escribe sobre el archivo que mide**, asi que las pruebas
tienen que verificar tambien que lo deje como estaba. Un instrumento que mide
bien pero corrompe el codigo es peor que no tenerlo.
"""

import argparse
import os
import shutil
import tempfile
import unittest

import contexto

mutation_checks = contexto.instrumento('mutation_checks')


FUENTE = 'def hay_lugar(capacidad, inscriptos):\n    return inscriptos < capacidad\n'

SIN_LIMITE = ('import unittest\nfrom cupos import hay_lugar\n\n\n'
              'class T(unittest.TestCase):\n'
              '    def test_hay(self):\n        self.assertIs(hay_lugar(10, 3), True)\n'
              '    def test_no_hay(self):\n        self.assertIs(hay_lugar(10, 20), False)\n')

CON_LIMITE = SIN_LIMITE + (
    '    def test_justo_lleno(self):\n        self.assertIs(hay_lugar(10, 10), False)\n'
    '    def test_uno_menos(self):\n        self.assertIs(hay_lugar(10, 9), True)\n')

SUITE_ROTA = SIN_LIMITE + (
    '    def test_roto(self):\n        self.assertIs(hay_lugar(1, 1), True)\n')

SIN_PRUEBAS = 'import unittest\n'


class MutacionTest(unittest.TestCase):

    def setUp(self):
        self.raiz = tempfile.mkdtemp(prefix='kddbook-mut-')
        self.addCleanup(shutil.rmtree, self.raiz, True)

    def _proyecto(self, nombre, pruebas, fuente=FUENTE):
        ruta = os.path.join(self.raiz, nombre)
        os.makedirs(ruta)
        for archivo, contenido in (('cupos.py', fuente), ('test_cupos.py', pruebas)):
            with open(os.path.join(ruta, archivo), 'w', encoding='utf-8',
                      newline='\n') as fh:
                fh.write(contenido)
        return ruta, os.path.join(ruta, 'cupos.py')

    def test_detecta_el_limite_sin_probar(self):
        proyecto, objetivo = self._proyecto('rojo', SIN_LIMITE)
        sobrevivientes, total = mutation_checks.check_limites(
            objetivo, proyecto, argparse.Namespace())
        self.assertTrue(sobrevivientes,
                        'la suite no prueba el caso lleno y el mutante sobrevivio '
                        'sin que el instrumento lo dijera')
        self.assertEqual(total, 1)

    def test_acepta_cuando_el_limite_esta_probado(self):
        proyecto, objetivo = self._proyecto('verde', CON_LIMITE)
        sobrevivientes, _total = mutation_checks.check_limites(
            objetivo, proyecto, argparse.Namespace())
        self.assertEqual(sobrevivientes, [])

    def test_avisa_si_la_suite_ya_estaba_en_rojo(self):
        """Con la suite rota no se puede saber si mata mutantes o falla sola."""
        proyecto, objetivo = self._proyecto('rota', SUITE_ROTA)
        with self.assertRaises(mutation_checks.NoVerificable):
            mutation_checks.check_limites(objetivo, proyecto, argparse.Namespace())

    def test_avisa_si_no_hay_pruebas(self):
        proyecto, objetivo = self._proyecto('vacia', SIN_PRUEBAS)
        with self.assertRaises(mutation_checks.NoVerificable):
            mutation_checks.check_limites(objetivo, proyecto, argparse.Namespace())

    def test_avisa_si_no_hay_limites_que_mutar(self):
        proyecto, objetivo = self._proyecto(
            'plana', 'import unittest\nfrom cupos import saludo\n\n\n'
                     'class T(unittest.TestCase):\n'
                     '    def test_saludo(self):\n'
                     "        self.assertEqual(saludo(), 'hola')\n",
            fuente="def saludo():\n    return 'hola'\n")
        with self.assertRaises(mutation_checks.NoVerificable):
            mutation_checks.check_limites(objetivo, proyecto, argparse.Namespace())

    def test_deja_el_archivo_como_estaba(self):
        """Mide mutando el archivo: si no lo restaura, rompe lo que mide."""
        proyecto, objetivo = self._proyecto('restaura', SIN_LIMITE)
        antes = open(objetivo, encoding='utf-8').read()
        mutation_checks.check_limites(objetivo, proyecto, argparse.Namespace())
        self.assertEqual(open(objetivo, encoding='utf-8').read(), antes,
                         'el instrumento dejo el archivo mutado')

    def test_todas_las_reglas_tienen_prueba(self):
        self.assertEqual(set(mutation_checks.RULES), {'limites'},
                         'hay reglas de mutacion sin prueba')


if __name__ == '__main__':
    unittest.main()
