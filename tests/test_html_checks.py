"""Los instrumentos de HTML contra fragmentos rojos y verdes.

Cada regla sale de una afirmacion comprobable de la documentacion de htmx, y
la prueba usa el ejemplo que la propia documentacion da. Las dos que dependen
de una declaracion —el nombre del header CSRF— traen ademas el caso en que
falta: ahi tienen que salir NO-VERIFICABLE y no verde.
"""

import argparse
import os
import shutil
import tempfile
import unittest

import contexto

H = contexto.instrumento('html_checks')


def _opts(**kwargs):
    base = dict(token=None)
    base.update(kwargs)
    return argparse.Namespace(**base)


class HtmlChecksTest(unittest.TestCase):

    def setUp(self):
        self.raiz = tempfile.mkdtemp(prefix='kddbook-html-')
        self.addCleanup(shutil.rmtree, self.raiz, True)

    def _elementos(self, html):
        ruta = os.path.join(self.raiz, 'pagina.html')
        with open(ruta, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(html)
        return H.parsear(ruta)

    def test_todas_las_reglas_tienen_prueba(self):
        probadas = {n.split('_')[1] for n in dir(self) if n.startswith('test_')}
        self.assertEqual(set(H.RULES) - probadas, set(),
                         'hay reglas de HTML sin prueba')

    # --------------------------------------------------------- progresivo
    def test_progresivo_detecta_y_acepta(self):
        # el ejemplo de la documentacion: hx-boost sobre un ancla con destino
        verde = self._elementos(
            '<div hx-boost="true">\n  <a href="/blog">Blog</a>\n</div>\n')
        self.assertEqual(H.check_progresivo(verde, _opts()), [])

        rojo = self._elementos('<button hx-post="/clicked">Click Me!</button>\n')
        hallazgos = H.check_progresivo(rojo, _opts())
        self.assertTrue(hallazgos, 'un boton suelto no degrada y no lo detecto')

    def test_progresivo_acepta_el_envoltorio_que_muestra_la_doc(self):
        """La doc arregla el ejemplo envolviendo el input en un <form action>."""
        envuelto = self._elementos(
            '<form action="/search" method="POST">\n'
            '  <input type="search" name="search" hx-post="/search">\n'
            '</form>\n')
        self.assertEqual(H.check_progresivo(envuelto, _opts()), [])

    # --------------------------------------------------------------- csrf
    def test_csrf_detecta_y_acepta(self):
        verde = self._elementos(
            '<body hx-headers=\'{"X-CSRF-TOKEN": "abc"}\'>\n'
            '  <button hx-post="/x">Enviar</button>\n</body>\n')
        self.assertEqual(H.check_csrf(verde, _opts(token='X-CSRF-TOKEN')), [])

        rojo = self._elementos('<body>\n  <button hx-post="/x">Enviar</button>\n</body>\n')
        self.assertTrue(H.check_csrf(rojo, _opts(token='X-CSRF-TOKEN')),
                        'no detecto la peticion sin token')

    def test_csrf_detecta_la_trampa_que_senala_la_doc(self):
        """Con hx-boost, <html> y <body> no se actualizan: el token queda viejo."""
        trampa = self._elementos(
            '<body hx-headers=\'{"X-CSRF-TOKEN": "abc"}\' hx-boost="true">\n'
            '  <a href="/x">ir</a>\n</body>\n')
        hallazgos = H.check_csrf(trampa, _opts(token='X-CSRF-TOKEN'))
        self.assertTrue(hallazgos, 'no detecto el token atrapado en <body> con hx-boost')
        self.assertIn('queda viejo', hallazgos[0][1])

    def test_csrf_acepta_el_input_oculto(self):
        """Muchos frameworks lo insertan como input; la doc lo alienta."""
        con_input = self._elementos(
            '<form action="/x" method="post">\n'
            '  <input type="hidden" name="x-csrf-token" value="abc">\n'
            '  <button hx-post="/x">Enviar</button>\n</form>\n')
        self.assertEqual(H.check_csrf(con_input, _opts(token='X-CSRF-TOKEN')), [])

    def test_csrf_avisa_si_no_se_declara_el_header(self):
        elementos = self._elementos('<button hx-post="/x">x</button>')
        with self.assertRaises(H.NoVerificable):
            H.check_csrf(elementos, _opts())

    def test_csrf_avisa_si_no_hay_peticiones_que_verificar(self):
        elementos = self._elementos('<p>una pagina sin htmx</p>')
        with self.assertRaises(H.NoVerificable):
            H.check_csrf(elementos, _opts(token='X-CSRF-TOKEN'))

    # ---------------------------------------------------------- indicador
    def test_indicador_detecta_y_acepta(self):
        verde = self._elementos(
            '<button hx-get="/x" hx-indicator="#spin">Ir</button>\n')
        self.assertEqual(H.check_indicador(verde, _opts()), [])

        rojo = self._elementos('<button hx-get="/x">Ir</button>\n')
        self.assertTrue(H.check_indicador(rojo, _opts()),
                        'no detecto la peticion sin indicador')

    def test_indicador_acepta_el_descendiente_con_la_clase(self):
        """El mecanismo por defecto: un hijo con class htmx-indicator."""
        verde = self._elementos(
            '<button hx-get="/x">Ir <img class="htmx-indicator" src="/s.gif"></button>\n')
        self.assertEqual(H.check_indicador(verde, _opts()), [])

    # ------------------------------------------------------------- arbol
    def test_un_elemento_vacio_no_adopta_a_sus_hermanos(self):
        """Lo que la lista VACIOS garantiza, comprobado donde se ve.

        La primera version de esta prueba miraba si el boton conservaba su
        ancestro y por eso no tenia dientes: `handle_endtag` recupera subiendo
        hasta el tag que cierra, asi que sacar el manejo de void elements
        cambia la FORMA del arbol pero no la alcanzabilidad de los ancestros.
        Lo que si cambia, y de forma observable, es que un `<img>` se quede con
        los hermanos que vienen despues como hijos.
        """
        elementos = self._elementos(
            '<div>\n  <img src="/a.png">\n'
            '  <button hx-get="/x">Ir</button>\n</div>\n')
        img = [e for e in elementos if e.tag == 'img'][0]
        self.assertEqual(img.hijos, [],
                         'el <img> adopto a su hermano: falta tratarlo como vacio')
        div = [e for e in elementos if e.tag == 'div'][0]
        self.assertEqual([h.tag for h in div.hijos], ['img', 'button'],
                         'los hermanos dejaron de ser hermanos')


if __name__ == '__main__':
    unittest.main()
