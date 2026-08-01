#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests para instruments/effective_go_checks.py.

Espejo estructural de tests/test_rust_api_checks.py: construye un proyecto
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

S = contexto.instrumento('effective_go_checks')

REGLAS = sorted(S.RULES)


class EffectiveGoChecks(unittest.TestCase):

    def setUp(self):
        self.raiz = tempfile.mkdtemp(prefix='effective_go_')

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

    def _correr(self, regla, texto, rel='main.go'):
        self._escribir(rel, texto)
        fuentes = S._fuentes(self.raiz)
        return S.RULES[regla][0](fuentes, self._opts())

    def _rojo(self, regla, texto, rel='main.go'):
        return len(self._correr(regla, texto, rel)) > 0

    def _verde(self, regla, texto, rel='main.go'):
        return self._correr(regla, texto, rel) == []

    # --- meta-registro -------------------------------------------------

    def test_todas_las_reglas_tienen_prueba(self):
        """Cada regla registrada en RULES tiene al menos un test asociado."""
        metodos = [m for m in dir(self) if m.startswith('test_')]
        for regla in REGLAS:
            nombre = regla.replace('-', '_')
            prefijo = 'test_{}'.format(nombre)
            self.assertTrue(
                any(m.startswith(prefijo) for m in metodos),
                'la regla `{}` carece de prueba.'.format(regla))

    def test_todas_las_funciones_check_estan_registradas(self):
        """Toda funcion check_* definida esta en RULES y viceversa
        (hyphens de la regla se tornan underscores en el nombre de la
        funcion)."""
        esperado = {'check_{}'.format(r.replace('-', '_')) for r in REGLAS}
        definidas = {
            n for n in dir(S)
            if n.startswith('check_') and callable(getattr(S, n))
        }
        self.assertEqual(
            definidas, esperado,
            'mismatch entre funciones check_* y reglas registradas: '
            '{} vs {}'.format(sorted(definidas), sorted(esperado)))

    def test_arquetipo_y_clase_no_verificable(self):
        """El artefacto es `proyecto` y NoVerificable es una excepcion."""
        self.assertEqual(S.ARTEFACTO, 'proyecto')
        self.assertTrue(issubclass(S.NoVerificable, Exception))

    def test_fuentes_rechaza_directorio_vacio(self):
        """Un proyecto sin .go levanta NoVerificable."""
        with self.assertRaises(S.NoVerificable):
            S._fuentes(self.raiz)

    # --- indentation-tabs -----------------------------------------------

    def test_indentation_tabs_detecta_y_acepta(self):
        """Las dos mitades de `indentation-tabs`: dispara sobre espacios,
        calla sobre tabs. Con una sola mitad, un instrumento que nunca
        dispara pasaria igual.
        """
        rojo = self._correr('indentation-tabs',
                            'package main\n\nimport "fmt"\n\n'
                            'func main() {\n'
                            '    fmt.Println("hola")\n'
                            '}\n')
        self.assertTrue(rojo, 'no detecto sangria de 4 espacios')
        self.assertIn('sangria', rojo[0][2])

        verde = self._correr('indentation-tabs',
                             'package main\n\nimport "fmt"\n\n'
                             'func main() {\n'
                             '\tfmt.Println("hola")\n'
                             '}\n')
        self.assertEqual(verde, [], 'marque tabulacion como violacion')

    def test_indentation_tabs_ignora_comentarios_bloque(self):
        """El contenido dentro de /* ... */ no se revisa por sangria."""
        texto = (
            'package main\n\n'
            '/*\n'
            '    este comentario usa espacios y no es violacion\n'
            ' */\n'
            'func main() {\n'
            '\tfmt.Println("ok")\n'
            '}\n')
        self.assertTrue(self._verde('indentation-tabs', texto))

    def test_indentation_tabs_ignora_archivos_de_test(self):
        """Los archivos *_test.go no se incluyen en las fuentes (convenio Go)."""
        self._escribir('main_test.go', '    fmt.Println("roto")\n')
        self._escribir('main.go', 'package main\n\nfunc main() {}\n')
        fuentes = S._fuentes(self.raiz)
        nombres = [os.path.basename(r) for r, _ in fuentes]
        self.assertIn('main.go', nombres)
        self.assertNotIn('main_test.go', nombres)

    # --- no-paren-control -----------------------------------------------

    def test_no_paren_control_detecta_y_acepta(self):
        """Las dos mitades de `no-paren-control`: dispara sobre parentesis,
        calla sobre la forma correcta.
        """
        rojo = self._correr('no-paren-control',
                            'package main\n\n'
                            'func main() {\n'
                            '    if (1 == 1) {\n'
                            '        fmt.Println("hola")\n'
                            '    }\n'
                            '}\n')
        self.assertTrue(rojo, 'no detecto parentesis en if')
        self.assertIn('if', rojo[0][2])

        verde = self._correr('no-paren-control',
                             'package main\n\n'
                             'func main() {\n'
                             '    if 1 == 1 {\n'
                             '        fmt.Println("hola")\n'
                             '    }\n'
                             '}\n')
        self.assertEqual(verde, [], 'marque if sin parentesis como violacion')

    def test_no_paren_control_detecta_for_y_switch(self):
        """for y switch tambien no usan parentesis en Go."""
        texto = ('package main\n\n'
                 'func main() {\n'
                 '    for (i := 0; i < 3; i++) {\n'
                 '    }\n'
                 '    switch (x) {\n'
                 '    case 1:\n'
                 '    }\n'
                 '}\n')
        rojo = self._correr('no-paren-control', texto)
        self.assertEqual(len(rojo), 2,
                         'no detecto parentesis en for y switch')

    def test_no_paren_control_no_marca_llamadas_a_funciones(self):
        """`foo(x)` no es una violacion: la keyword debe ser if/for/switch."""
        texto = ('package main\n\n'
                 'func foo(x int) int { return x + 1 }\n\n'
                 'func main() {\n'
                 '    fmt.Println(foo(1))\n'
                 '}\n')
        self.assertTrue(self._verde('no-paren-control', texto))

    # --- brace-next-line ------------------------------------------------

    def test_brace_next_line_detecta_y_acepta(self):
        """Las dos mitades de `brace-next-line`: dispara sobre llave en
        linea separada, calla sobre llave en la misma linea.
        """
        rojo = self._correr('brace-next-line',
                            'package main\n\n'
                            'func main() {\n'
                            '    if 1 == 1\n'
                            '    {\n'
                            '        fmt.Println("hola")\n'
                            '    }\n'
                            '}\n')
        self.assertTrue(rojo, 'no detecto brace-next-line')
        self.assertIn('llave', rojo[0][2])

        verde = self._correr('brace-next-line',
                             'package main\n\n'
                             'func main() {\n'
                             '    if 1 == 1 {\n'
                             '        fmt.Println("hola")\n'
                             '    }\n'
                             '}\n')
        self.assertEqual(verde, [], 'marque brace en la misma linea como violacion')

    def test_brace_next_line_acepta_palabras_clave_variadas(self):
        """Las tres keywords (if, for, switch) con brace en la misma linea son OK."""
        texto = ('package main\n\n'
                 'func main() {\n'
                 '    for i := 0; i < 3; i++ {\n'
                 '    }\n'
                 '    switch x {\n'
                 '    case 1:\n'
                 '    }\n'
                 '    if x {\n'
                 '    }\n'
                 '}\n')
        self.assertTrue(self._verde('brace-next-line', texto))

    def test_brace_next_line_no_marca_llave_de_cierre(self):
        """Una llave de cierre `}` en linea separada no es violacion."""
        texto = ('package main\n\n'
                 'func main() {\n'
                 '    if 1 == 1 {\n'
                 '    }\n'
                 '}\n')
        self.assertTrue(self._verde('brace-next-line', texto))


if __name__ == '__main__':
    unittest.main()
