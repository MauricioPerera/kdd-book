"""Los instrumentos de Tailwind contra proyectos rojos y verdes.

El artefacto es nuevo —HTML/JSX con clases, CSS con @theme— y cada regla se
arma un proyecto minimo en un temporal, igual que `entorno_checks`.
"""

import argparse
import os
import shutil
import sys
import tempfile
import unittest

import contexto  # noqa: F401  (por su efecto: ver su docstring)

import tailwind_checks as W


class TailwindChecksTest(unittest.TestCase):

    def setUp(self):
        self.raiz = tempfile.mkdtemp(prefix='kddbook-tw-')
        self.addCleanup(shutil.rmtree, self.raiz, True)

    def _proyecto(self, archivos):
        for nombre, contenido in archivos.items():
            ruta = os.path.join(self.raiz, nombre.replace('/', os.sep))
            os.makedirs(os.path.dirname(ruta), exist_ok=True)
            with open(ruta, 'w', encoding='utf-8', newline='\n') as fh:
                fh.write(contenido)
        return self.raiz

    def _opts(self, **kwargs):
        base = dict(proyecto=self.raiz, propiedades=None)
        base.update(kwargs)
        return argparse.Namespace(**base)

    def _correr(self, regla, archivos, **kwargs):
        self._proyecto(archivos)
        return W.RULES[regla][0](self.raiz, self._opts(**kwargs))

    def test_todas_las_reglas_tienen_prueba(self):
        metodos = [n for n in dir(self) if n.startswith('test_')]
        sin_prueba = [r for r in W.RULES
                     if not any(m.startswith('test_' + r.replace('-', '_'))
                                for m in metodos)]
        self.assertEqual(sin_prueba, [], 'hay reglas de tailwind sin prueba')

    def test_todas_las_funciones_check_estan_registradas(self):
        definidas = {n[len('check_'):].replace('_', '-') for n in dir(W)
                    if n.startswith('check_')}
        self.assertEqual(definidas - set(W.RULES), set(),
                         'hay checks escritos que el instrumento no puede ejecutar')

    # ------------------------------------------------------------ instalacion
    def test_instalacion_detecta_y_acepta(self):
        rojo = self._correr('instalacion',
                            {'vite.config.ts': 'export default {}\n',
                             'src/app.css': 'body { margin: 0; }\n'})
        self.assertTrue(rojo, 'no detecto la falta del plugin y del import')

        verde = self._correr('instalacion',
                             {'vite.config.ts': ('import tailwindcss from '
                                                 '"@tailwindcss/vite";\n'
                                                 'export default { plugins: '
                                                 '[tailwindcss()] };\n'),
                              'src/app.css': '@import "tailwindcss";\n'})
        self.assertEqual(verde, [])

    def test_instalacion_sin_vite_no_mide(self):
        with self.assertRaises(W.NoVerificable):
            self._correr('instalacion', {'src/app.css': 'body { margin: 0; }\n'})

    # ---------------------------------------------------------- preprocesadores
    def test_preprocesadores_detecta_y_acepta(self):
        manifiesto_rojo = '{"dependencies": {"tailwindcss": "^4.0.0", "sass": "^1.0.0"}}\n'
        rojo = self._correr('preprocesadores', {'package.json': manifiesto_rojo})
        self.assertTrue(rojo, 'no detecto sass junto con tailwindcss')

        manifiesto_verde = '{"dependencies": {"tailwindcss": "^4.0.0"}}\n'
        verde = self._correr('preprocesadores', {'package.json': manifiesto_verde})
        self.assertEqual(verde, [])

    def test_preprocesadores_detecta_por_archivo_ademas_de_por_dependencia(self):
        manifiesto = '{"dependencies": {"tailwindcss": "^4.0.0"}}\n'
        rojo = self._correr('preprocesadores',
                            {'package.json': manifiesto, 'src/app.scss': 'body{}\n'})
        self.assertTrue(rojo, 'no detecto el archivo .scss')

    def test_preprocesadores_sin_tailwindcss_declarado_no_mide(self):
        with self.assertRaises(W.NoVerificable):
            self._correr('preprocesadores', {'package.json': '{"dependencies": {}}\n'})

    def test_preprocesadores_sin_manifiesto_no_mide(self):
        with self.assertRaises(W.NoVerificable):
            self._correr('preprocesadores', {'index.html': '<html></html>\n'})

    # --------------------------------------------------------------- referencia
    def test_referencia_detecta_y_acepta(self):
        rojo = self._correr('referencia',
                            {'C.vue': '<template></template>\n'
                                     '<style>\n.a { @apply flex; }\n</style>\n'})
        self.assertTrue(rojo, 'no detecto @apply sin @reference')

        verde = self._correr('referencia',
                             {'C.vue': '<template></template>\n'
                                      '<style>\n@reference "../app.css";\n'
                                      '.a { @apply flex; }\n</style>\n'})
        self.assertEqual(verde, [])

    def test_referencia_sin_componentes_no_mide(self):
        with self.assertRaises(W.NoVerificable):
            self._correr('referencia', {'index.html': '<html></html>\n'})

    # ---------------------------------------------------------- utilidades removidas
    def test_utilidades_removidas_detecta_y_acepta(self):
        rojo = self._correr('utilidades-removidas',
                            {'index.html': '<div class="bg-opacity-50"></div>\n'})
        self.assertTrue(rojo, 'no detecto bg-opacity-50')

        verde = self._correr('utilidades-removidas',
                             {'index.html': '<div class="bg-black/50"></div>\n'})
        self.assertEqual(verde, [])

    def test_utilidades_removidas_no_marca_las_renombradas(self):
        """`shadow` sigue siendo valida en v4, solo que con otra escala."""
        verde = self._correr('utilidades-removidas',
                             {'index.html': '<div class="shadow rounded ring"></div>\n'})
        self.assertEqual(verde, [], 'marco una utilidad renombrada, no removida')

    def test_utilidades_removidas_cubre_toda_la_familia_flex_shrink(self):
        rojo = self._correr('utilidades-removidas',
                            {'index.html': '<div class="flex-shrink-2"></div>\n'})
        self.assertTrue(rojo, 'flex-shrink-* se removio entera, no solo -0/-1')

    # ------------------------------------------------------- modificador important
    def test_modificador_important_detecta_y_acepta(self):
        rojo = self._correr('modificador-important',
                            {'index.html': '<div class="!flex"></div>\n'})
        self.assertTrue(rojo, 'no detecto el prefijo !')

        verde = self._correr('modificador-important',
                             {'index.html': '<div class="flex!"></div>\n'})
        self.assertEqual(verde, [])

    def test_modificador_important_detecta_con_variante(self):
        rojo = self._correr('modificador-important',
                            {'index.html': '<div class="!hover:bg-red-500"></div>\n'})
        self.assertTrue(rojo, 'no detecto el prefijo ! delante de una variante')

    # ------------------------------------------------------ utilidades en conflicto
    def test_utilidades_en_conflicto_detecta_y_acepta(self):
        rojo = self._correr('utilidades-en-conflicto',
                            {'index.html': '<div class="flex hidden"></div>\n'})
        self.assertTrue(rojo, 'no detecto flex e hidden sobre display')

        verde = self._correr('utilidades-en-conflicto',
                             {'index.html': '<div class="flex items-center"></div>\n'})
        self.assertEqual(verde, [])

    def test_utilidades_en_conflicto_ignora_las_variantes(self):
        """md:hidden y flex no compiten: aplican en breakpoints distintos."""
        verde = self._correr('utilidades-en-conflicto',
                             {'index.html': '<div class="flex md:hidden"></div>\n'})
        self.assertEqual(verde, [])

    def test_utilidades_en_conflicto_respeta_el_mapa_declarado(self):
        ruta = os.path.join(self.raiz, 'propiedades.json')
        with open(ruta, 'w', encoding='utf-8') as fh:
            fh.write('{"foo": "custom-prop", "bar": "custom-prop"}\n')
        rojo = self._correr('utilidades-en-conflicto',
                            {'index.html': '<div class="foo bar"></div>\n'},
                            propiedades=ruta)
        self.assertTrue(rojo, 'no uso el mapa declarado con --propiedades')

    # ------------------------------------------------------------- mobile-first
    def test_mobile_first_detecta_y_acepta(self):
        rojo = self._correr('mobile-first',
                            {'index.html': '<div class="sm:text-center"></div>\n'})
        self.assertTrue(rojo, 'no detecto la utilidad solo bajo sm:')

        verde = self._correr('mobile-first',
                             {'index.html': '<div class="text-center sm:text-left">'
                                            '</div>\n'})
        self.assertEqual(verde, [])

    def test_mobile_first_acepta_una_sola_utilidad_sin_prefijo(self):
        self.assertEqual(self._correr('mobile-first',
                                      {'index.html': '<div class="flex"></div>\n'}), [])

    # ------------------------------------------------------------ theme variables
    def test_theme_variables_detecta_y_acepta(self):
        rojo = self._correr('theme-variables',
                            {'app.css': ':root {\n  --color-brand: oklch(0.7 0.1 20);\n}\n'})
        self.assertTrue(rojo, 'no detecto la variable de tema declarada con :root')

        verde = self._correr('theme-variables',
                             {'app.css': '@theme {\n  --color-brand: oklch(0.7 0.1 20);\n}\n'})
        self.assertEqual(verde, [])

    def test_theme_variables_detecta_el_theme_anidado(self):
        rojo = self._correr('theme-variables',
                            {'app.css': '@media (min-width: 1px) {\n'
                                       '  @theme {\n    --color-brand: red;\n  }\n}\n'})
        self.assertTrue(rojo, 'no detecto @theme anidado en un @media')

    def test_theme_variables_sin_css_no_mide(self):
        with self.assertRaises(W.NoVerificable):
            self._correr('theme-variables', {'index.html': '<html></html>\n'})

    # -------------------------------------------------------------- namespace color
    def test_namespace_color_detecta_y_acepta(self):
        rojo = self._correr('namespace-color',
                            {'app.css': '@theme {\n  --brand: oklch(0.7 0.1 20);\n}\n'})
        self.assertTrue(rojo, 'no detecto el color fuera de --color-*')

        verde = self._correr('namespace-color',
                             {'app.css': '@theme {\n  --color-brand: oklch(0.7 0.1 20);\n}\n'})
        self.assertEqual(verde, [])

    def test_namespace_color_sin_variables_con_forma_de_color_no_mide(self):
        """Sin ningun valor con forma de color, no hay nada que verificar."""
        with self.assertRaises(W.NoVerificable):
            self._correr('namespace-color', {'app.css': '@theme {\n  --spacing-lg: 2rem;\n}\n'})

    def test_namespace_color_no_marca_lo_que_ya_esta_en_el_namespace_correcto(self):
        verde = self._correr('namespace-color',
                             {'app.css': '@theme {\n  --spacing-lg: 2rem;\n'
                                        '  --color-brand: oklch(0.7 0.1 20);\n}\n'})
        self.assertEqual(verde, [], 'marco --spacing-lg, que no tiene forma de color')

    # ------------------------------------------------------------- clases dinamicas
    def test_clases_dinamicas_detecta_y_acepta(self):
        rojo = self._correr('clases-dinamicas',
                            {'t.html': '<p class="text-{{ error ? \'red\' : \'green\' }}-600">'
                                      '</p>\n'})
        self.assertTrue(rojo, 'no detecto la interpolacion dentro de class')

        verde = self._correr('clases-dinamicas',
                             {'t.html': '<p class="{{ error ? \'text-red-600\' : '
                                       '\'text-green-600\' }}"></p>\n'})
        self.assertTrue(verde, 'esto SI deberia marcarse: la interpolacion sigue '
                              'estando, solo que ahora rodea toda la clase')

    def test_clases_dinamicas_acepta_clases_completas_estaticas(self):
        verde = self._correr('clases-dinamicas',
                             {'t.jsx': '<div className="bg-blue-600 hover:bg-blue-500">'
                                      '</div>\n'})
        self.assertEqual(verde, [])

    def test_clases_dinamicas_detecta_template_literal_de_jsx(self):
        """`className={...}` usa llaves, no comillas: necesita su propio patron."""
        rojo = self._correr('clases-dinamicas',
                            {'t.jsx': '<div className={`bg-${color}-600`}></div>\n'})
        self.assertTrue(rojo, 'no detecto el template literal con interpolacion')


if __name__ == '__main__':
    unittest.main()
