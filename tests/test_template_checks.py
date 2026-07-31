"""El instrumento de plantillas contra fragmentos rojos y verdes.

La regla depende de una declaracion del proyecto —el motor, y para jinja2 y
django tambien el estado del autoescape— asi que buena parte de estas pruebas
es que **la declaracion ausente salga NO-VERIFICABLE y no verde**. Ese es el
punto de la regla 1 de htmx: la misma plantilla es segura o no segun algo que
no esta escrito en ella, y un instrumento que lo adivinara diria "limpio"
sobre una plantilla que inyecta.
"""

import argparse
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..',
                                'instruments'))

import template_checks as T  # noqa: E402


def _opts(**kwargs):
    base = dict(motor=None, autoescape=None)
    base.update(kwargs)
    return argparse.Namespace(**base)


def _archivos(texto, nombre='plantilla.html'):
    return [(nombre, texto)]


class TemplateChecksTest(unittest.TestCase):

    def test_todas_las_reglas_tienen_prueba(self):
        probadas = {n.split('_')[1] for n in dir(self) if n.startswith('test_')}
        self.assertEqual(set(T.RULES) - probadas, set(),
                         'hay reglas de plantillas sin prueba')

    def test_todas_las_funciones_check_estan_registradas(self):
        """Un check fuera de RULES es codigo muerto que no mide nada.

        Existe porque ya paso: `check_g29` se escribio, se probo y nunca se
        registro. Comparar los casos de prueba contra RULES no lo detecta —
        falta en los dos lados.
        """
        definidas = {n[len('check_'):] for n in dir(T) if n.startswith('check_')}
        self.assertEqual(definidas - set(T.RULES), set(),
                         'hay checks escritos que el instrumento no puede ejecutar')

    # ------------------------------------------------- jinja2 y django
    def test_escapado_acepta_el_autoescape_encendido(self):
        verde = _archivos('<p>{{ comentario }}</p>\n')
        self.assertEqual(
            T.check_escapado(verde, _opts(motor='jinja2', autoescape='on')), [])

    def test_escapado_detecta_la_salida_de_escape(self):
        """`|safe` con autoescape on es justo lo que la regla 1 prohibe."""
        rojo = _archivos('<p>{{ comentario|safe }}</p>\n')
        hallazgos = T.check_escapado(rojo, _opts(motor='jinja2', autoescape='on'))
        self.assertTrue(hallazgos, 'no detecto el |safe')
        self.assertIn('salida de escape', hallazgos[0][2])

    def test_escapado_detecta_el_autoescape_apagado(self):
        rojo = _archivos('<p>{{ comentario }}</p>\n')
        hallazgos = T.check_escapado(rojo, _opts(motor='jinja2', autoescape='off'))
        self.assertTrue(hallazgos, 'con autoescape off toda interpolacion entra cruda')

    def test_escapado_acepta_el_filtro_explicito_con_el_global_apagado(self):
        """Escapar una por una tambien resuelve; el umbral es cero, no un metodo."""
        verde = _archivos('<p>{{ comentario|e }}</p>\n')
        self.assertEqual(
            T.check_escapado(verde, _opts(motor='jinja2', autoescape='off')), [])

    def test_escapado_sigue_los_bloques_de_autoescape(self):
        texto = ('<p>{{ a }}</p>\n'
                 '{% autoescape false %}\n'
                 '<p>{{ b }}</p>\n'
                 '{% endautoescape %}\n'
                 '<p>{{ c }}</p>\n')
        hallazgos = T.check_escapado(_archivos(texto),
                                     _opts(motor='jinja2', autoescape='on'))
        self.assertEqual([h[1] for h in hallazgos], [3],
                         'el bloque tiene que abrir y CERRAR: solo b esta cruda')

    def test_escapado_ignora_lo_que_esta_comentado(self):
        texto = '{# {{ viejo|safe }} #}\n<p>{{ a }}</p>\n'
        self.assertEqual(
            T.check_escapado(_archivos(texto), _opts(motor='jinja2', autoescape='on')),
            [], 'marco en rojo una interpolacion que esta en un comentario')

    def test_escapado_reporta_la_linea_correcta_tras_un_comentario_largo(self):
        """Blanquear preserva los saltos; borrar correria todo lo de abajo."""
        texto = '{# uno\ndos\ntres #}\n<p>{{ a|safe }}</p>\n'
        hallazgos = T.check_escapado(_archivos(texto),
                                     _opts(motor='jinja2', autoescape='on'))
        self.assertEqual([h[1] for h in hallazgos], [4])

    def test_escapado_usa_la_salida_de_escape_de_django(self):
        """Cada motor tiene la suya: mark_safe no es Markup."""
        rojo = _archivos('<p>{{ mark_safe(x) }}</p>\n')
        self.assertTrue(
            T.check_escapado(rojo, _opts(motor='django', autoescape='on')))
        self.assertEqual(
            T.check_escapado(rojo, _opts(motor='jinja2', autoescape='on')), [],
            'mark_safe no es la salida de jinja2: marcarla seria medir otro motor')

    def test_escapado_usa_la_salida_de_escape_de_jinja2(self):
        """La simetrica de la anterior, y hace falta las dos.

        Con una sola direccion, agregarle a un motor la salida del otro pasa
        sin que nadie lo note: el instrumento quedaria midiendo una union de
        motores en vez del que el proyecto declaro.
        """
        rojo = _archivos('<p>{{ Markup(x) }}</p>\n')
        self.assertTrue(
            T.check_escapado(rojo, _opts(motor='jinja2', autoescape='on')))
        self.assertEqual(
            T.check_escapado(rojo, _opts(motor='django', autoescape='on')), [],
            'Markup no es la salida de django')

    # ------------------------------------------- handlebars y mustache
    def test_escapado_detecta_el_triple_stache(self):
        rojo = _archivos('<p>{{{ comentario }}}</p>\n')
        hallazgos = T.check_escapado(rojo, _opts(motor='handlebars'))
        self.assertTrue(hallazgos, 'no detecto el triple stache')
        self.assertIn('triple', hallazgos[0][2])

    def test_escapado_cuenta_el_triple_una_sola_vez(self):
        """`{{{x}}}` contiene un `{{x}}`: sin blanquearlo se cuenta dos veces.

        Mira el CONTADOR y no los hallazgos, que es donde el defecto se ve. La
        primera version de esta prueba miraba `check_escapado` y por eso no
        tenia dientes: sacar el blanqueo no agrega ningun hallazgo, infla el
        total. Y el total es lo que decide si hay algo que medir — sin el, una
        plantilla sin interpolaciones podria pasar por medida.
        """
        total, hallazgos = T._analizar_por_interpolacion('<p>{{{ x }}}</p>\n',
                                                         'handlebars')
        self.assertEqual(total, 1, 'el triple se conto tambien como interpolacion simple')
        self.assertEqual(len(hallazgos), 1)

        total, _ = T._analizar_por_interpolacion('<p>{{& x }}</p>\n', 'mustache')
        self.assertEqual(total, 1, 'el ampersand se conto dos veces')

    def test_escapado_detecta_el_ampersand(self):
        rojo = _archivos('<p>{{& comentario }}</p>\n')
        self.assertTrue(T.check_escapado(rojo, _opts(motor='mustache')))

    def test_escapado_no_confunde_secciones_con_valores(self):
        """Tambien mira el contador, por el mismo motivo que el triple.

        Una seccion mal contada no produce hallazgos —no hay nada que reportar
        sobre `{{#lista}}`— asi que el unico lugar donde el defecto se ve es el
        total, y con el total inflado una plantilla de puras secciones pasaria
        por una plantilla medida.
        """
        texto = '{{#lista}}\n  <li>{{ nombre }}</li>\n{{/lista}}\n'
        self.assertEqual(T.check_escapado(_archivos(texto),
                                          _opts(motor='handlebars')), [])
        total, _ = T._analizar_por_interpolacion(texto, 'handlebars')
        self.assertEqual(total, 1,
                         'la apertura y el cierre de seccion se contaron como valores')

    # ------------------------------------------------------ declaraciones
    def test_escapado_avisa_si_no_se_declara_el_motor(self):
        with self.assertRaises(T.NoVerificable):
            T.check_escapado(_archivos('<p>{{ a }}</p>'), _opts())

    def test_escapado_avisa_si_falta_el_autoescape(self):
        """Sin el dato, la MISMA plantilla es segura o no. No se puede medir."""
        with self.assertRaises(T.NoVerificable):
            T.check_escapado(_archivos('<p>{{ a }}</p>'), _opts(motor='jinja2'))

    def test_escapado_rechaza_el_autoescape_donde_no_aplica(self):
        """Aceptarlo callado haria creer que la declaracion sirvio para algo."""
        with self.assertRaises(T.NoVerificable):
            T.check_escapado(_archivos('<p>{{ a }}</p>'),
                             _opts(motor='handlebars', autoescape='on'))

    def test_escapado_avisa_si_no_hay_interpolaciones(self):
        """Verde sobre una plantilla estatica seria decir que se midio algo."""
        with self.assertRaises(T.NoVerificable):
            T.check_escapado(_archivos('<p>hola</p>\n'),
                             _opts(motor='jinja2', autoescape='on'))

    def test_escapado_no_cuenta_las_constantes_como_contenido_de_usuario(self):
        with self.assertRaises(T.NoVerificable):
            T.check_escapado(_archivos('<p>{{ "-" }}</p>\n'),
                             _opts(motor='jinja2', autoescape='off'))


if __name__ == '__main__':
    unittest.main()
