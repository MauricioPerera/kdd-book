"""Los instrumentos de accesibilidad contra paginas rojas y verdes.

Cada regla sale de un criterio de WCAG que nombra un mecanismo, y la prueba arma
la pagina minima que lo incumple. Las dos que comparan valores renderizados
—contraste y area de toque— traen ademas el caso en que no hay nada que leer:
ahi tienen que salir NO-VERIFICABLE y no verde, que es la diferencia entre "no
lo puedo medir" y "esta bien".
"""

import argparse
import json
import os
import shutil
import tempfile
import unittest

import contexto

A = contexto.instrumento('a11y_checks')


class A11yChecksTest(unittest.TestCase):

    def setUp(self):
        self.raiz = tempfile.mkdtemp(prefix='kddbook-a11y-')
        self.addCleanup(shutil.rmtree, self.raiz, True)

    def _opts(self, **kwargs):
        base = dict(min=4.5, min_grande=3.0, medidas=None, estilos=[])
        base.update(kwargs)
        return argparse.Namespace(**base)

    def _pagina(self, html):
        ruta = os.path.join(self.raiz, 'pagina.html')
        with open(ruta, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(html)
        return A.parsear(ruta)

    def _json(self, datos):
        ruta = os.path.join(self.raiz, 'medidas.json')
        with open(ruta, 'w', encoding='utf-8', newline='\n') as fh:
            json.dump(datos, fh)
        return ruta

    def _correr(self, regla, html, **kwargs):
        return A.RULES[regla][0](self._pagina(html), self._opts(**kwargs))

    def test_todas_las_reglas_tienen_prueba(self):
        probadas = {n.split('_')[1] for n in dir(self) if n.startswith('test_')}
        self.assertEqual(set(A.RULES) - probadas, set(),
                         'hay reglas de accesibilidad sin prueba')

    def test_todas_las_funciones_check_estan_registradas(self):
        definidas = {n[len('check_'):] for n in dir(A) if n.startswith('check_')}
        self.assertEqual(definidas - set(A.RULES), set(),
                         'hay checks escritos que el instrumento no puede ejecutar')

    # --------------------------------------------------------- autocomplete
    def test_autocomplete_detecta_y_acepta(self):
        rojo = self._correr('autocomplete', '<input type="email" name="correo">\n')
        self.assertTrue(rojo, 'un campo de email sin autocomplete no se detecto')
        verde = self._correr('autocomplete',
                             '<input type="email" name="correo" autocomplete="email">\n')
        self.assertEqual(verde, [])

    def test_autocomplete_rechaza_un_token_inventado(self):
        """La lista la enumera el criterio: por eso se exige pertenencia."""
        rojo = self._correr('autocomplete',
                            '<input type="text" autocomplete="nombre-completo">\n')
        self.assertTrue(rojo)
        self.assertIn('no esta en la lista', rojo[0][1])

    def test_autocomplete_acepta_los_modificadores_del_criterio(self):
        verde = self._correr('autocomplete',
                             '<input autocomplete="shipping street-address">\n')
        self.assertEqual(verde, [])

    # -------------------------------------------------------------- autoplay
    def test_autoplay_detecta_y_acepta(self):
        self.assertTrue(self._correr('autoplay', '<audio autoplay src="a.mp3"></audio>\n'))
        self.assertEqual(self._correr('autoplay',
                                      '<audio autoplay muted src="a.mp3"></audio>\n'), [])
        self.assertEqual(self._correr('autoplay',
                                      '<audio autoplay controls src="a.mp3"></audio>\n'), [])

    # ------------------------------------------------------------- contraste
    def test_contraste_detecta_y_acepta(self):
        rojo = self._correr('contraste',
                            '<p style="color:#777;background-color:#fff">hola</p>\n')
        self.assertTrue(rojo, 'gris medio sobre blanco no llega a 4.5:1')

        verde = self._correr('contraste',
                             '<p style="color:#000;background-color:#fff">hola</p>\n')
        self.assertEqual(verde, [], 'negro sobre blanco es 21:1')

    def test_contraste_calcula_la_razon_de_la_norma(self):
        """Negro sobre blanco es 21:1 exacto: si la formula esta mal, no da 21."""
        self.assertAlmostEqual(A._razon((0, 0, 0), (255, 255, 255)), 21.0, places=6)
        self.assertAlmostEqual(A._razon((255, 255, 255), (255, 255, 255)), 1.0, places=6)

    def test_contraste_afloja_el_umbral_con_texto_grande(self):
        """#949494 sobre blanco da 3.03:1: pasa el umbral grande y no el chico.

        El color esta elegido para caer ENTRE los dos umbrales, y ese es el
        unico color con el que la prueba sirve. El primer intento uso #767676,
        que da 4.54 y pasa los dos: la prueba se veia igual y se quedaba verde
        aunque se borrara la distincion de tamano.
        """
        html = '<p style="color:#949494;background-color:#fff;font-size:32px">a</p>\n'
        self.assertEqual(self._correr('contraste', html), [],
                         'con texto grande el minimo es 3:1 y ese par lo pasa')
        chico = html.replace('font-size:32px', 'font-size:12px')
        self.assertTrue(self._correr('contraste', chico),
                        'con texto chico el minimo es 4.5:1 y ese par no llega')

    def test_contraste_lee_las_medidas_declaradas(self):
        ruta = self._json({'boton primario': {'color': '#888', 'fondo': '#999'}})
        rojo = self._correr('contraste', '<p>sin estilos</p>\n', medidas=ruta)
        self.assertTrue(rojo)
        self.assertIn('boton primario', rojo[0][1])

    def test_contraste_rechaza_un_minimo_imposible(self):
        """21:1 es el maximo posible: un minimo mayor no lo cumple nadie.

        Lo encontro correr las diez reglas de una sola pasada con el mismo
        `--min`: `contraste` y `toque` lo comparten, y 24 —que son pixeles— se
        leyo como una razon. El instrumento se ponia rojo sobre una pagina
        impecable sin dar ninguna pista.
        """
        with self.assertRaises(A.NoVerificable):
            self._correr('contraste',
                         '<p style="color:#000;background-color:#fff">a</p>\n',
                         min=24)

    def test_contraste_sin_nada_que_leer_no_mide(self):
        """El umbral es perfecto y lo que compara no esta en el HTML."""
        with self.assertRaises(A.NoVerificable):
            self._correr('contraste', '<p>hola</p>\n')

    def test_contraste_avisa_si_no_sabe_leer_el_color(self):
        with self.assertRaises(A.NoVerificable):
            self._correr('contraste',
                         '<p style="color:rebeccapurple;background-color:#fff">a</p>\n')

    # -------------------------------------------------------------- etiqueta
    def test_etiqueta_detecta_y_acepta(self):
        self.assertTrue(self._correr('etiqueta', '<input type="text" id="a">\n'))
        self.assertEqual(self._correr('etiqueta',
                                      '<label for="a">Nombre</label><input id="a">\n'), [])

    def test_etiqueta_acepta_el_label_que_envuelve(self):
        verde = self._correr('etiqueta', '<label>Nombre <input type="text"></label>\n')
        self.assertEqual(verde, [])

    def test_etiqueta_no_acepta_el_placeholder(self):
        """Desaparece al escribir: no es un nombre, es una pista."""
        self.assertTrue(self._correr('etiqueta',
                                     '<input type="text" placeholder="Nombre">\n'))

    def test_etiqueta_ignora_los_controles_que_no_piden_nada(self):
        verde = self._correr('etiqueta',
                             '<input type="hidden" name="csrf">'
                             '<input type="submit" value="Enviar">\n')
        self.assertEqual(verde, [])

    # ------------------------------------------------------ etiquetaennombre
    def test_etiquetaennombre_detecta_y_acepta(self):
        rojo = self._correr('etiquetaennombre',
                            '<button aria-label="Enviar formulario">Buscar</button>\n')
        self.assertTrue(rojo, 'quien dice "buscar" en voz alta no activa ese boton')

        verde = self._correr('etiquetaennombre',
                             '<button aria-label="Buscar en el catalogo">Buscar</button>\n')
        self.assertEqual(verde, [])

    def test_etiquetaennombre_necesita_las_dos_cosas_para_comparar(self):
        self.assertEqual(self._correr('etiquetaennombre',
                                      '<button aria-label="Cerrar"></button>\n'), [])
        self.assertEqual(self._correr('etiquetaennombre', '<button>Cerrar</button>\n'), [])

    # ---------------------------------------------------------------- idioma
    def test_idioma_detecta_y_acepta(self):
        self.assertTrue(self._correr('idioma', '<html><body>hola</body></html>\n'))
        self.assertEqual(self._correr('idioma',
                                      '<html lang="es-AR"><body>hola</body></html>\n'), [])

    def test_idioma_rechaza_lo_que_no_tiene_forma_de_etiqueta(self):
        for malo in ('espanol', 'es_AR', '  '):
            with self.subTest(lang=malo):
                self.assertTrue(self._correr(
                    'idioma', '<html lang="{}"><body>x</body></html>\n'.format(malo)))

    def test_idioma_no_mide_un_fragmento(self):
        with self.assertRaises(A.NoVerificable):
            self._correr('idioma', '<div>un fragmento</div>\n')

    # ------------------------------------------------------------ movimiento
    def test_movimiento_detecta_y_acepta(self):
        rojo = self._correr('movimiento',
                            '<style>.x { animation: girar 2s; }</style>\n')
        self.assertTrue(rojo)
        verde = self._correr(
            'movimiento',
            '<style>.x { animation: girar 2s; }\n'
            '@media (prefers-reduced-motion: reduce) { .x { animation: none; } }</style>\n')
        self.assertEqual(verde, [])

    def test_movimiento_no_pide_nada_si_no_hay_animaciones(self):
        self.assertEqual(self._correr('movimiento', '<style>.x { color: red; }</style>\n'), [])

    def test_movimiento_sin_estilos_no_mide(self):
        with self.assertRaises(A.NoVerificable):
            self._correr('movimiento', '<p>una pagina sin estilos</p>\n')

    # ------------------------------------------------------------- nombrerol
    def test_nombrerol_detecta_y_acepta(self):
        self.assertTrue(self._correr('nombrerol', '<div role="button"></div>\n'))
        self.assertEqual(self._correr('nombrerol', '<div role="button">Cerrar</div>\n'), [])

    def test_nombrerol_detecta_el_aria_inventado(self):
        """Un aria que no existe no rompe nada y no hace nada: nadie avisa."""
        rojo = self._correr('nombrerol', '<div aria-etiqueta="Cerrar">x</div>\n')
        self.assertTrue(rojo)
        self.assertIn('no existe', rojo[0][1])

    def test_nombrerol_acepta_el_aria_valido(self):
        self.assertEqual(self._correr('nombrerol', '<div aria-hidden="true">x</div>\n'), [])

    def test_nombrerol_no_toma_por_nombre_lo_que_nadie_ve(self):
        """El contenido de `script` y `style` no es texto visible.

        Sin esta prueba la exclusion no tenia dientes: la escribi en
        `texto_visible()`, la explique en su docstring y ninguna prueba la
        tocaba. Sacarla dejaba el instrumento en verde sobre un boton cuyo
        unico "nombre" es un pedazo de javascript que no se lee ni se ve.
        """
        rojo = self._correr('nombrerol',
                            '<div role="button"><script>cerrar()</script></div>\n')
        self.assertTrue(rojo, 'tomo el codigo del <script> como nombre accesible')
        rojo = self._correr('nombrerol',
                            '<div role="button"><style>.x{color:red}</style></div>\n')
        self.assertTrue(rojo, 'tomo el CSS del <style> como nombre accesible')

    # ---------------------------------------------------------------- saltar
    def test_saltar_detecta_y_acepta(self):
        self.assertTrue(self._correr('saltar', '<body><h1>Titulo</h1></body>\n'))
        self.assertEqual(self._correr(
            'saltar', '<a href="#c">Saltar al contenido</a><div id="c">x</div>\n'), [])

    def test_saltar_acepta_la_region_principal(self):
        self.assertEqual(self._correr('saltar', '<body><main>x</main></body>\n'), [])

    def test_saltar_no_acepta_un_enlace_a_un_ancla_inexistente(self):
        self.assertTrue(self._correr('saltar', '<a href="#contenido">Saltar</a>\n'),
                        'un salto a un destino que no existe no saltea nada')

    # ----------------------------------------------------------------- toque
    def test_toque_detecta_y_acepta(self):
        rojo = self._correr('toque', '<a style="width:16px;height:16px">x</a>\n', min=24)
        self.assertTrue(rojo)
        verde = self._correr('toque', '<a style="width:24px;height:24px">x</a>\n', min=24)
        self.assertEqual(verde, [])

    def test_toque_usa_el_umbral_que_se_le_pide(self):
        html = '<a style="width:24px;height:24px">x</a>\n'
        self.assertEqual(self._correr('toque', html, min=24), [])
        self.assertTrue(self._correr('toque', html, min=44),
                        'el nivel AAA pide 44 y 24 no alcanza')

    def test_toque_sin_nada_que_medir_no_mide(self):
        with self.assertRaises(A.NoVerificable):
            self._correr('toque', '<a href="/x">sin medidas</a>\n')


if __name__ == '__main__':
    unittest.main()
