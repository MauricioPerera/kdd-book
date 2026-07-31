"""Los instrumentos de la guia de Google contra prosa roja y verde.

De las 42 reglas, 36 se miden solo con la prosa y van en una tabla, igual que
`test_pep8_checks`. Las otras 6 dependen de un vocabulario que el proyecto
declara —terminos, nombres de producto, lenguaje inclusivo, jerga, tipos de
aviso— y van en metodos aparte, con el caso de la declaracion ausente.
"""

import argparse
import json
import os
import shutil
import sys
import tempfile
import unittest

import contexto  # noqa: F401  (por su efecto: ver su docstring)

import prosa_checks as P


# regla -> (fragmento rojo, fragmento verde)
CASOS = {
    'minimizadores': ('Simply click the button to continue.\n',
                      'Click the button to continue.\n'),
    'tiempo-relativo': ('This feature is currently in beta.\n',
                       'This feature is in beta as of version 3.\n'),
    'abreviaturas-latinas': ('Use a config file, e.g. config.yaml.\n',
                            'Use a config file, for example config.yaml.\n'),
    'encabezados-caja': ('# Setting Up Your Development Environment\n',
                        '# Setting up your development environment\n'),
    'plural-parentesis': ('Delete the file(s) you no longer need.\n',
                         'Delete the files you no longer need.\n'),
    'tiempo-futuro': ('The server will return an error.\n',
                      'The server returns an error.\n'),
    'pronombres-genero': ('Ask the user for his password.\n',
                         'Ask the user for their password.\n'),
    'primera-persona': ('We recommend that we restart the service.\n',
                       'You should restart the service.\n'),
    'mayuscula-dos-puntos': ('Note: this happens because the cache was not cleared.\n',
                            'Note: cache not cleared.\n'),
    'coma-serial': ('The output has apples, bananas and cherries.\n',
                    'The output has apples, bananas, and cherries.\n'),
    'raya': ('The result — unexpected — surprised everyone.\n',
            'The result—unexpected—surprised everyone.\n'),
    'puntos-suspensivos': ('The list continues...\n',
                          'The list continues…\n'),
    'parentesis-anidados': ('The value (in seconds (approximately)) varies.\n',
                           'The value (in seconds, approximately) varies.\n'),
    'punto-final': ('First step.  Second step.\n',
                    'First step. Second step.\n'),
    'comillas-puntuacion': ('Set the mode to "auto".\n',
                           'Set the mode to "auto."\n'),
    'and-or': ('Use a cat/dog picture for testing.\n',
              'Use a cat or dog picture for testing.\n'),
    'fechas': ('The change ships on July 1st.\n',
              'The change ships on July 1.\n'),
    'alt-texto': ('![](diagram.png)\n', '![Architecture diagram](diagram.png)\n'),
    'notas-pie': ('The API is stable.[^1]\n', 'The API is stable, per the changelog.\n'),
    'encabezados-unicos': ('# Setup.\n\n## Options\n\n# Setup.\n',
                          '# Setup\n\n## Options\n'),
    'items-lista': ('- first item\n- Second item\n', '- First item\n- Second item\n'),
    'numeros-chicos': ('Wait 3 seconds before retrying.\n', 'Wait 3s before retrying.\n'),
    'telefonos': ('Call us at 415-555-2671.\n', 'Call us at 415-555-0123.\n'),
    'procedimientos': ('1. You open the console.\n2. Click Save.\n',
                      '1. Open the console.\n2. Click Save.\n'),
    'tablas-encabezado': ('| a | b |\n| 1 | 2 |\n', '| a | b |\n|---|---|\n| 1 | 2 |\n'),
    'unidades': ('The file is 10kg heavier than expected.\n',
                'The file is 10 kg heavier than expected.\n'),
    'texto-enlace': ('See [here](https://example.com/docs) for details.\n',
                    'See the [configuration guide](https://example.com/docs) for details.\n'),
    'anclas': ('See [Options](#options).\n', '## Options\n\nSee [Options](#options).\n'),
    'sintaxis-cli': ('gcloud deploy --region (optional)\n', 'gcloud deploy [--region REGION]\n'),
    'marcadores': ('Replace YOUR_PROJECT_ID with your project.\n',
                  'Replace <project-id> with your project.\n'),
    'verbos-interaccion': ('Click on Save to continue.\n', 'Click Save to continue.\n'),
    'html-en-markdown': ('Some text <div>and a raw tag</div>.\n', 'Some text and no raw tag.\n'),
    'dominios': ('Visit acmecorp.com for pricing.\n', 'Visit example.com for pricing.\n'),
    'nombres-archivo': ('See My_Config.md for details.\n', 'See my-config.md for details.\n'),
    'notacion-matematica': ('The area is $a \\times b$ or 3 * 4.\n', 'The area is $a \\times b$.\n'),
    'bloques-codigo': ('```\n' + 'x' * 90 + '\n```\n', '```\nx = 1\n```\n'),
}


def _opts(**kwargs):
    base = dict(lista=None, productos=None, inclusivo=None, jerga=None,
               avisos=None, ancho_codigo=80)
    base.update(kwargs)
    return argparse.Namespace(**base)


class ProsaChecksTest(unittest.TestCase):

    def setUp(self):
        self.raiz = tempfile.mkdtemp(prefix='kddbook-prosa-')
        self.addCleanup(shutil.rmtree, self.raiz, True)

    def _documento(self, texto, nombre='doc.md'):
        ruta = os.path.join(self.raiz, nombre)
        with open(ruta, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(texto)
        return P.Documento(ruta)

    def _json(self, datos):
        ruta = os.path.join(self.raiz, 'lista.json')
        with open(ruta, 'w', encoding='utf-8', newline='\n') as fh:
            json.dump(datos, fh)
        return ruta

    def _correr(self, regla, texto, nombre='doc.md', **kwargs):
        return P.RULES[regla][0](self._documento(texto, nombre), _opts(**kwargs))

    def test_toda_regla_tiene_su_par_o_prueba_dedicada(self):
        dedicadas = {'lista-palabras', 'nombres-producto', 'posesivo-producto',
                    'inclusivo', 'jerga', 'avisos-tipo'}
        self.assertEqual(set(P.RULES) - set(CASOS) - dedicadas, set(),
                         'hay reglas sin caso de prueba')
        self.assertEqual(set(CASOS) - set(P.RULES), set(),
                         'hay casos de prueba para reglas que no existen')

    def test_todas_las_funciones_check_estan_registradas(self):
        definidas = {n[len('check_'):].replace('_', '-') for n in dir(P)
                    if n.startswith('check_')}
        registradas = set(P.RULES)
        self.assertEqual(definidas - registradas, set(),
                         'hay checks escritos que el instrumento no puede ejecutar')

    def test_cada_regla_detecta_su_rojo(self):
        for regla, (rojo, _verde) in sorted(CASOS.items()):
            with self.subTest(regla=regla):
                self.assertTrue(self._correr(regla, rojo),
                                'la regla no detecto su propio caso rojo')

    def test_cada_regla_acepta_su_verde(self):
        for regla, (_rojo, verde) in sorted(CASOS.items()):
            with self.subTest(regla=regla):
                self.assertEqual(self._correr(regla, verde), [],
                                 'la regla marco su propio caso verde')

    # ------------------------------------------------------ vocabulario declarado
    def test_lista_palabras_detecta_y_acepta(self):
        ruta = self._json({'sign in': 'log in'})
        rojo = self._correr('lista-palabras', 'Please sign in to continue.\n', lista=ruta)
        self.assertTrue(rojo)
        self.assertIn('log in', rojo[0][1])
        verde = self._correr('lista-palabras', 'Please log in to continue.\n', lista=ruta)
        self.assertEqual(verde, [])

    def test_lista_palabras_sin_declarar_no_mide(self):
        with self.assertRaises(P.NoVerificable):
            self._correr('lista-palabras', 'Please sign in.\n')

    def test_nombres_producto_detecta_y_acepta(self):
        ruta = self._json(['Google Cloud'])
        rojo = self._correr('nombres-producto', 'Deploy it on google cloud.\n',
                            productos=ruta)
        self.assertTrue(rojo)
        verde = self._correr('nombres-producto', 'Deploy it on Google Cloud.\n',
                             productos=ruta)
        self.assertEqual(verde, [])

    def test_nombres_producto_sin_declarar_no_mide(self):
        with self.assertRaises(P.NoVerificable):
            self._correr('nombres-producto', 'Deploy it on google cloud.\n')

    def test_posesivo_producto_detecta_y_acepta(self):
        ruta = self._json(['Google Docs'])
        rojo = self._correr('posesivo-producto',
                            "Open Google Docs's sharing menu.\n", productos=ruta)
        self.assertTrue(rojo)
        verde = self._correr('posesivo-producto',
                             'Open the Google Docs sharing menu.\n', productos=ruta)
        self.assertEqual(verde, [])

    def test_inclusivo_detecta_y_acepta(self):
        ruta = self._json(['whitelist'])
        rojo = self._correr('inclusivo', 'Add the domain to the whitelist.\n',
                            inclusivo=ruta)
        self.assertTrue(rojo)
        verde = self._correr('inclusivo', 'Add the domain to the allowlist.\n',
                             inclusivo=ruta)
        self.assertEqual(verde, [])

    def test_inclusivo_sin_declarar_no_mide(self):
        with self.assertRaises(P.NoVerificable):
            self._correr('inclusivo', 'Add the domain to the whitelist.\n')

    def test_jerga_detecta_y_acepta(self):
        ruta = self._json(['idempotent'])
        rojo = self._correr('jerga', 'The operation is idempotent.\n', jerga=ruta)
        self.assertTrue(rojo)
        verde = self._correr('jerga', 'Running it twice has the same effect.\n',
                             jerga=ruta)
        self.assertEqual(verde, [])

    def test_avisos_tipo_detecta_y_acepta(self):
        ruta = self._json(['Note', 'Warning'])
        rojo = self._correr('avisos-tipo', '**Heads up:** this may take a while.\n',
                            avisos=ruta)
        self.assertTrue(rojo)
        verde = self._correr('avisos-tipo', '**Note:** this may take a while.\n',
                             avisos=ruta)
        self.assertEqual(verde, [])

    def test_avisos_tipo_sin_declarar_no_mide(self):
        with self.assertRaises(P.NoVerificable):
            self._correr('avisos-tipo', '**Note:** this may take a while.\n')

    # ------------------------------------------------------------- sutilezas
    def test_html_en_markdown_solo_mide_archivos_md(self):
        with self.assertRaises(P.NoVerificable):
            self._correr('html-en-markdown', 'Some <div>text</div>.\n', nombre='doc.txt')

    def test_mascarar_no_mide_dentro_de_codigo(self):
        """`e.g.` dentro de un bloque de codigo no es una violacion de prosa."""
        texto = '```\n# e.g. this is a comment\n```\n'
        self.assertEqual(self._correr('abreviaturas-latinas', texto), [])

    def test_coma_serial_no_marca_una_lista_de_dos(self):
        self.assertEqual(self._correr('coma-serial', 'It has apples and bananas.\n'), [])

    def test_bloques_codigo_respeta_el_ancho_declarado(self):
        texto = '```\n' + 'x' * 50 + '\n```\n'
        self.assertEqual(self._correr('bloques-codigo', texto), [])
        self.assertTrue(self._correr('bloques-codigo', texto, ancho_codigo=30))


if __name__ == '__main__':
    unittest.main()
