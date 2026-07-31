"""Los instrumentos de arquitectura contra proyectos reales en temporales.

Cada regla necesita su caso rojo y su caso verde, y las que dependen de una
declaracion (capas, esquema, modulos de negocio) necesitan ademas el caso en
que la declaracion falta: ahi tienen que salir NO-VERIFICABLE y no verde.
Confundir "no puedo saber" con "esta limpio" es el fallo silencioso que toda
esta familia existe para no cometer.
"""

__all__ = ['ArchChecksTest']

import argparse
import os
import shutil
import tempfile
import unittest

import contexto

arch_checks = contexto.instrumento('arch_checks')


def _opts(**kwargs):
    base = dict(capa=None, permite=None, permite_crear=None, negocio=None,
                esquema=None, max_sin_usar=0)
    base.update(kwargs)
    return argparse.Namespace(**base)


class ArchChecksTest(unittest.TestCase):
    """Cada regla de arquitectura contra un proyecto roto y uno sano."""

    def setUp(self):
        """SetUp."""
        self.raiz = tempfile.mkdtemp(prefix='kddbook-arch-')
        self.addCleanup(shutil.rmtree, self.raiz, True)

    def _proyecto(self, nombre, archivos):
        ruta = os.path.join(self.raiz, nombre)
        for relativo, contenido in archivos.items():
            destino = os.path.join(ruta, relativo.replace('/', os.sep))
            os.makedirs(os.path.dirname(destino), exist_ok=True)
            with open(destino, 'w', encoding='utf-8', newline='\n') as fh:
                fh.write(contenido)
        return ruta

    def test_todas_las_reglas_tienen_prueba(self):
        """Todas las reglas tienen prueba."""
        probadas = {n.split('_')[1] for n in dir(self) if n.startswith('test_')}
        self.assertEqual(set(arch_checks.RULES) - probadas, set(),
                         'hay reglas de arquitectura sin prueba')

    # ------------------------------------------------------------- capas
    CAPAS = _opts(capa=['presentacion=vistas', 'negocio=servicios',
                        'persistencia=dao'],
                  permite=['presentacion>negocio', 'negocio>persistencia'])

    def test_capas_detecta_y_acepta(self):
        """Las dos mitades de `capas`: dispara sobre el caso roto y calla
        sobre el sano. Con una sola, un instrumento que nunca dispara
        pasaria igual.
        """
        verde = self._proyecto('capv', {
            'vistas/pantalla.py': 'from servicios.libros import Servicio\n',
            'servicios/libros.py': 'from dao.libros import LibroDAO\n\n\nclass Servicio:\n    pass\n',
            'dao/libros.py': 'class LibroDAO:\n    pass\n',
        })
        self.assertEqual(arch_checks.check_capas(verde, self.CAPAS), [])

        rojo = self._proyecto('capr', {
            'vistas/pantalla.py': 'from dao.libros import LibroDAO\n',
            'servicios/libros.py': 'class Servicio:\n    pass\n',
            'dao/libros.py': 'class LibroDAO:\n    pass\n',
        })
        hallazgos = arch_checks.check_capas(rojo, self.CAPAS)
        self.assertTrue(hallazgos, 'no detecto la presentacion importando persistencia')
        self.assertFalse(hallazgos[0][1])

    def test_capas_avisa_si_no_hay_capas_declaradas(self):
        """Capas avisa si no hay capas declaradas."""
        proyecto = self._proyecto('capn', {'a.py': 'x = 1\n'})
        with self.assertRaises(arch_checks.NoVerificable):
            arch_checks.check_capas(proyecto, _opts())

    # ----------------------------------------------------- instanciacion
    def test_instanciacion_detecta_y_acepta(self):
        """Las dos mitades de `instanciacion`: dispara sobre el caso roto y calla
        sobre el sano. Con una sola, un instrumento que nunca dispara
        pasaria igual.
        """
        verde = self._proyecto('insv', {
            'dao.py': 'class LibroDAO:\n    pass\n',
            'servicio.py': 'from dao import LibroDAO\n\n\nclass Servicio:\n'
                           '    def __init__(self, dao):\n        self.dao = dao\n',
        })
        self.assertEqual(arch_checks.check_instanciacion(verde, _opts()), [])

        rojo = self._proyecto('insr', {
            'dao.py': 'class LibroDAO:\n    pass\n',
            'servicio.py': 'from dao import LibroDAO\n\n\nclass Servicio:\n'
                           '    def __init__(self):\n        self.dao = LibroDAO()\n',
        })
        self.assertTrue(arch_checks.check_instanciacion(rojo, _opts()),
                        'no detecto la clase creando a su colaborador')

    def test_instanciacion_exime_a_la_factoria(self):
        """La factoria existe justo para crear: marcarla seria absurdo."""
        proyecto = self._proyecto('insf', {
            'dao.py': 'class LibroDAO:\n    pass\n',
            'factoria.py': 'from dao import LibroDAO\n\n\nclass Factoria:\n'
                           '    def crear(self):\n        return LibroDAO()\n',
        })
        self.assertEqual(
            arch_checks.check_instanciacion(proyecto, _opts(permite_crear=['factoria'])),
            [])

    # ------------------------------------------------------- excepciones
    def test_excepciones_detecta_y_acepta(self):
        """Las dos mitades de `excepciones`: dispara sobre el caso roto y calla
        sobre el sano. Con una sola, un instrumento que nunca dispara
        pasaria igual.
        """
        verde = self._proyecto('excv', {
            'a.py': 'def f(t):\n    try:\n        return int(t)\n'
                    '    except ValueError:\n        return 0\n'})
        self.assertEqual(arch_checks.check_excepciones(verde, _opts()), [])

        rojo = self._proyecto('excr', {
            'a.py': 'def f(t):\n    try:\n        return int(t)\n'
                    '    except:\n        return 0\n'})
        self.assertTrue(arch_checks.check_excepciones(rojo, _opts()))

        vacio = self._proyecto('excz', {
            'a.py': 'def f(t):\n    try:\n        return int(t)\n'
                    '    except ValueError:\n        pass\n'})
        self.assertTrue(arch_checks.check_excepciones(vacio, _opts()),
                        'no detecto el bloque except vacio')

    # --------------------------------------------------------------- isp
    def test_isp_detecta_y_acepta(self):
        """Las dos mitades de `isp`: dispara sobre el caso roto y calla
        sobre el sano. Con una sola, un instrumento que nunca dispara
        pasaria igual.
        """
        verde = self._proyecto('ispv', {
            'a.py': 'class Repositorio:\n'
                    '    def buscar(self):\n        return 1\n\n\n'
                    'class Cliente:\n'
                    '    def usar(self, repo: Repositorio):\n'
                    '        return repo.buscar()\n'})
        self.assertEqual(arch_checks.check_isp(verde, _opts()), [])

        rojo = self._proyecto('ispr', {
            'a.py': 'class Repositorio:\n'
                    '    def buscar(self):\n        return 1\n'
                    '    def guardar(self):\n        return 2\n'
                    '    def borrar(self):\n        return 3\n\n\n'
                    'class Cliente:\n'
                    '    def usar(self, repo: Repositorio):\n'
                    '        return repo.buscar()\n'})
        self.assertTrue(arch_checks.check_isp(rojo, _opts()),
                        'no detecto al cliente dependiendo de metodos que no usa')

    # --------------------------------------------------------------- aop
    def test_aop_detecta_y_acepta(self):
        """Las dos mitades de `aop`: dispara sobre el caso roto y calla
        sobre el sano. Con una sola, un instrumento que nunca dispara
        pasaria igual.
        """
        verde = self._proyecto('aopv', {
            'negocio/tarifas.py': 'def total(x):\n    return x * 2\n'})
        self.assertEqual(
            arch_checks.check_aop(verde, _opts(negocio=['negocio'])), [])

        rojo = self._proyecto('aopr', {
            'negocio/tarifas.py': 'import logging\n\n\ndef total(x):\n'
                                  '    logging.info("calculando")\n    return x * 2\n'})
        self.assertTrue(
            arch_checks.check_aop(rojo, _opts(negocio=['negocio'])),
            'no detecto el logging dentro del negocio')

    def test_aop_avisa_si_no_se_declara_el_negocio(self):
        """Aop avisa si no se declara el negocio."""
        proyecto = self._proyecto('aopn', {'a.py': 'x = 1\n'})
        with self.assertRaises(arch_checks.NoVerificable):
            arch_checks.check_aop(proyecto, _opts())

    # --------------------------------------------------------------- coc
    def _esquema(self, contenido):
        ruta = os.path.join(self.raiz, 'esquema.json')
        with open(ruta, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(contenido)
        return ruta

    def test_coc_detecta_y_acepta(self):
        """Las dos mitades de `coc`: dispara sobre el caso roto y calla
        sobre el sano. Con una sola, un instrumento que nunca dispara
        pasaria igual.
        """
        esquema = self._esquema('{"Libro": ["titulo", "autor", "anio"]}')
        verde = self._proyecto('cocv', {
            'a.py': 'class Libro:\n    def __init__(self, t, a, n):\n'
                    '        self.titulo = t\n        self.autor = a\n'
                    '        self.anio = n\n'})
        self.assertEqual(arch_checks.check_coc(verde, _opts(esquema=esquema)), [])

        rojo = self._proyecto('cocr', {
            'a.py': 'class Libro:\n    def __init__(self, t, a):\n'
                    '        self.titulo = t\n        self.escritor = a\n'})
        self.assertTrue(arch_checks.check_coc(rojo, _opts(esquema=esquema)),
                        'no detecto los campos que no siguen la convencion')

    def test_coc_avisa_si_no_hay_esquema(self):
        """Coc avisa si no hay esquema."""
        proyecto = self._proyecto('cocn', {'a.py': 'x = 1\n'})
        with self.assertRaises(arch_checks.NoVerificable):
            arch_checks.check_coc(proyecto, _opts())


if __name__ == '__main__':
    unittest.main()
