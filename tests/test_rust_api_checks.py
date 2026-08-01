#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests para instruments/rust_api_checks.py.

Espejo estructural de tests/test_stripe_checks.py: construye un proyecto
falso en un directorio temporal, ejecuta `S._fuentes` y cada `check_*`
registrada en `RULES`, verificando mitades rojas/verdes y la integridad
del registro de reglas.
"""

import argparse
import os
import shutil
import tempfile
import unittest

import contexto

S = contexto.instrumento('rust_api_checks')

REGLAS = sorted(S.RULES)


class RustApiChecks(unittest.TestCase):

    def setUp(self):
        self.raiz = tempfile.mkdtemp(prefix='rust_api_')

    def tearDown(self):
        shutil.rmtree(self.raiz, ignore_errors=True)

    # --- utilidades ----------------------------------------------------

    def _opts(self, **kw):
        base = {'proyecto': self.raiz}
        base.update(kw)
        return argparse.Namespace(**base)

    def _escribir(self, rel, texto):
        ruta = os.path.join(self.raiz, rel)
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, 'w', encoding='utf-8') as fh:
            fh.write(texto)
        return ruta

    def _correr(self, regla, texto, rel='lib.rs'):
        self._escribir(rel, texto)
        fuentes = S._fuentes(self.raiz)
        return S.RULES[regla][0](fuentes, self._opts())

    def _rojo(self, regla, texto, rel='lib.rs'):
        return len(self._correr(regla, texto, rel)) > 0

    def _verde(self, regla, texto, rel='lib.rs'):
        return self._correr(regla, texto, rel) == []

    # --- meta-registro -------------------------------------------------

    def test_todas_las_reglas_tienen_prueba(self):
        """Cada regla registra tiene al menos un test asociado."""
        for regla in REGLAS:
            nombre = regla.replace('-', '_')
            prefijo = 'test_{}'.format(nombre)
            metodos = [m for m in dir(self) if m.startswith('test_')]
            self.assertTrue(
                any(m.startswith(prefijo) for m in metodos),
                'la regla `{}` carece de prueba.'.format(regla))

    def test_todas_las_funciones_check_estan_registradas(self):
        """Toda funcion check_* definida tiene su regla en RULES y
        viceversa (hyphens de la regla se tornan underscores en el
        nombre de la funcion)."""
        esperado = {'check_{}'.format(r.replace('-', '_')) for r in REGLAS}
        definidas = {
            n for n in dir(S)
            if n.startswith('check_') and callable(getattr(S, n))
        }
        self.assertEqual(
            definidas, esperado,
            'mismatch entre funciones check_* y reglas registradas: '
            '{} vs {}'.format(sorted(definidas), sorted(esperado)))

    # --- getter (C-GETTER) --------------------------------------------

    def test_getter_detecta_devolucion_por_valor(self):
        texto = (
            'pub struct Contador;\n\n'
            'impl Contador {\n'
            '    pub fn get_count(&self) -> u32 {\n'
            '        0\n'
            '    }\n'
            '}\n')
        self.assertTrue(self._rojo('getter', texto))

    def test_getter_acepta_referencia(self):
        texto = (
            'pub struct Contador;\n\n'
            'impl Contador {\n'
            '    pub fn get_total(&self) -> &u32 {\n'
            '        &0\n'
            '    }\n'
            '}\n')
        self.assertTrue(self._verde('getter', texto))

    def test_getter_acepta_nombre_sin_prefijo(self):
        texto = (
            'pub struct Contador;\n\n'
            'impl Contador {\n'
            '    pub fn count(&self) -> u32 {\n'
            '        0\n'
            '    }\n'
            '}\n')
        self.assertTrue(self._verde('getter', texto))

    def test_getter_ignora_test_files(self):
        self._escribir('test_lib.rs',
                       'pub fn get_count(&self) -> u32 { 0 }')
        self._escribir('lib.rs', 'pub struct Contador;\n')
        fuentes = S._fuentes(self.raiz)
        self.assertEqual(
            S.RULES['getter'][0](fuentes, self._opts()), [])

    # --- common-traits (C-COMMON-TRAITS) ------------------------------

    def test_common_traits_detecta_struct_sin_debug(self):
        self.assertTrue(self._rojo('common-traits', 'pub struct Foo;\n'))

    def test_common_traits_acepta_derive_debug(self):
        self.assertTrue(self._verde(
            'common-traits',
            '#[derive(Debug)]\npub struct Foo;\n'))

    def test_common_traits_no_marca_no_publico(self):
        self.assertTrue(self._verde('common-traits', 'struct Foo;\n'))

    def test_common_traits_acepta_enum_derivado(self):
        self.assertTrue(self._verde(
            'common-traits',
            '#[derive(Debug, Clone)]\npub enum Bar { A, B }\n'))

    # --- question-mark (C-QUESTION-MARK) ------------------------------

    def test_question_mark_detecta_unwrap(self):
        texto = (
            '/// ```rust\n'
            '/// let r = foo().unwrap();\n'
            '/// ```\n'
            'pub fn foo() -> Result<u32, ()> { Ok(0) }\n')
        self.assertTrue(self._rojo('question-mark', texto))

    def test_question_mark_acepta_interrogacion(self):
        texto = (
            '/// ```rust\n'
            '/// let r = foo()?;\n'
            '/// ```\n'
            'pub fn foo() -> Result<u32, ()> { Ok(0) }\n')
        self.assertTrue(self._verde('question-mark', texto))

    def test_question_mark_sin_doc_no_marca(self):
        texto = 'pub fn foo() -> Result<u32, ()> { Ok(0) }\n'
        self.assertTrue(self._verde('question-mark', texto))

    def test_question_mark_detecta_try(self):
        texto = (
            '/// ```rust\n'
            '/// let r = try!(foo());\n'
            '/// ```\n'
            'pub fn foo() -> Result<u32, ()> { Ok(0) }\n')
        self.assertTrue(self._rojo('question-mark', texto))

    def test_question_mark_no_marca_unwrap_fuera_de_fences(self):
        texto = (
            '/// Comentario de doc sin bloque de codigo.\n'
            '/// Usa foo().unwrap() en la prosa.\n'
            'pub fn foo() -> Result<u32, ()> { Ok(0) }\n')
        self.assertTrue(self._verde('question-mark', texto))


if __name__ == '__main__':
    unittest.main()
