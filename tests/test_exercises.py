"""Coherencia de cada ejercicio: el seed, la solucion y el `kind` declarado.

Existe por un error concreto. En el ejercicio G29 declare `kind: refactor` y
escribi un seed que **cambiaba el comportamiento** (`cupos != 0` contra
`cupos > 0`, distinto para negativos). El contrato decia "el comportamiento no
cambia" y era falso. Lo detecto el oraculo al correrlo a mano; esta prueba lo
detecta sola.

Lo que se verifica en cada ejercicio:

- el instrumento esta **verde sobre la solucion** (si no, la solucion no
  resuelve lo que el contrato pide);
- el instrumento esta **rojo sobre el seed** (si no, el ejercicio ya viene
  hecho y el instrumento no discrimina nada);
- el oraculo se comporta como manda el `kind` declarado.

Hay tres formas de ejercicio y solo una deja el oraculo en rojo:

| kind | oraculo sobre el seed | por que |
|---|---|---|
| `refactor` | verde | una refactorizacion no cambia el comportamiento observable |
| `nivel-repo` | verde | la funcionalidad esta intacta; lo que falta es el flujo de trabajo |
| `cambio-de-interfaz` | rojo | la tecnica cambia la firma y el oraculo tiene que notarlo |

Que el oraculo quede ciego en dos de las tres no es un defecto: es la razon de
ser del instrumento. Si los tests bastaran, no harian falta.
"""

__all__ = ['CoherenciaTest']

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
EJERCICIOS = os.path.join(RAIZ, 'exercises')
INSTRUMENTOS = os.path.join(RAIZ, 'instruments')

# Formas de ejercicio segun que se espera del oraculo sobre el seed.
ORACULO_CIEGO = {'refactor', 'nivel-repo'}
ORACULO_ROJO = {'cambio-de-interfaz'}


def _specs():
    """Todos los ejercicios de todos los libros, no solo los del primero."""
    for libro in sorted(os.listdir(EJERCICIOS)):
        raiz_libro = os.path.join(EJERCICIOS, libro)
        if not os.path.isdir(raiz_libro):
            continue
        for nombre in sorted(os.listdir(raiz_libro)):
            ruta = os.path.join(raiz_libro, nombre, 'spec.json')
            if os.path.isfile(ruta):
                with open(ruta, 'r', encoding='utf-8') as fh:
                    yield '{}/{}'.format(libro, nombre), json.load(fh)


def _nativo(ruta):
    return ruta.replace('/', os.sep)


class CoherenciaTest(unittest.TestCase):
    """Cada ejercicio contra su seed, su solucion y su `kind`."""

    def setUp(self):
        """SetUp."""
        self.tmp = tempfile.mkdtemp(prefix='kddbook-ej-')
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _copiar(self, nombre):
        destino = os.path.join(self.tmp, nombre.replace('/', '_'))
        shutil.copytree(os.path.join(EJERCICIOS, _nativo(nombre)), destino,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        return destino

    def _preparar(self, base, spec):
        """Corre el paso de preparacion, si el ejercicio declara uno.

        Tiene que estar porque el gate lo corre: sin esto la prueba mediria una
        secuencia distinta de la que se ejecuta de verdad, y los contratos que
        derivan su artefacto del target —las respuestas HTTP que produce la
        app— salian con exit 2 por medir capturas que todavia no existian.
        """
        preparar = spec.get('preparar')
        if not preparar:
            return
        ruta = os.path.join(base, _nativo(preparar))
        subprocess.run([sys.executable, os.path.basename(ruta)],
                       cwd=os.path.dirname(ruta), capture_output=True, text=True)

    def _instrumento(self, base, spec):
        self._preparar(base, spec)
        instrumento = spec['instrument']
        cmd = ([sys.executable, os.path.join(INSTRUMENTOS, instrumento['script'])]
               + list(instrumento.get('args', []))
               + [os.path.join(base, _nativo(spec.get('target', 'target.py')))])
        return subprocess.run(cmd, cwd=base, capture_output=True, text=True).returncode

    def _oraculo(self, base, spec):
        oraculo = os.path.join(base, _nativo(spec.get('oracle', 'oracle_test.py')))
        return subprocess.run(
            [sys.executable, '-m', 'unittest',
             os.path.splitext(os.path.basename(oraculo))[0]],
            cwd=os.path.dirname(oraculo), capture_output=True, text=True).returncode

    def _poner_seed(self, base, spec):
        origen = os.path.join(base, _nativo(spec.get('seed', 'seed.py')))
        shutil.copyfile(origen, os.path.join(base, _nativo(spec.get('target', 'target.py'))))

    def test_hay_ejercicios(self):
        """Hay ejercicios."""
        self.assertTrue(list(_specs()), 'no se encontro ningun ejercicio')

    def test_instrumento_verde_sobre_la_solucion(self):
        """Instrumento verde sobre la solucion."""
        for nombre, spec in _specs():
            with self.subTest(ejercicio=nombre):
                base = self._copiar(nombre)
                self.assertEqual(self._instrumento(base, spec), 0,
                                 'la solucion de referencia no satisface su propio instrumento')

    def test_instrumento_rojo_sobre_el_seed(self):
        """Instrumento rojo sobre el seed."""
        for nombre, spec in _specs():
            with self.subTest(ejercicio=nombre):
                base = self._copiar(nombre)
                self._poner_seed(base, spec)
                self.assertEqual(self._instrumento(base, spec), 1,
                                 'el instrumento no distingue el seed de la solucion: '
                                 'el ejercicio ya viene hecho o el instrumento no mide')

    def test_el_kind_declarado_es_conocido(self):
        """El kind declarado es conocido."""
        for nombre, spec in _specs():
            with self.subTest(ejercicio=nombre):
                self.assertIn(spec.get('kind', 'refactor'), ORACULO_CIEGO | ORACULO_ROJO,
                              'kind desconocido: no se sabe que esperar del oraculo')

    def test_el_oraculo_concuerda_con_el_kind_declarado(self):
        """El oraculo concuerda con el kind declarado."""
        for nombre, spec in _specs():
            with self.subTest(ejercicio=nombre):
                base = self._copiar(nombre)
                self._poner_seed(base, spec)
                codigo = self._oraculo(base, spec)
                if spec.get('kind', 'refactor') in ORACULO_CIEGO:
                    self.assertEqual(
                        codigo, 0,
                        'declarado {!r} pero el oraculo se pone rojo sobre el seed: '
                        'entonces el seed cambia el comportamiento y el contrato '
                        'miente al decir que no cambia'.format(spec.get('kind')))
                else:
                    self.assertNotEqual(
                        codigo, 0,
                        'declarado cambio de interfaz pero el oraculo pasa sobre el '
                        'seed: el oraculo no esta escrito contra la firma de destino')

    def test_el_oraculo_pasa_sobre_la_solucion(self):
        """El oraculo pasa sobre la solucion."""
        for nombre, spec in _specs():
            with self.subTest(ejercicio=nombre):
                base = self._copiar(nombre)
                self.assertEqual(self._oraculo(base, spec), 0,
                                 'la solucion de referencia no pasa su propio oraculo')


if __name__ == '__main__':
    unittest.main()
