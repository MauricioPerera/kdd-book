"""Los instrumentos de HTTP contra capturas rojas y verdes.

Las dos reglas salen de afirmaciones comprobables de la documentacion de htmx.
Las dos traen ademas el caso en que **no se puede saber**: sin dos capturas
comparables no hay como demostrar que la respuesta varia, y sin directivas
declaradas "tener una CSP" no significa nada. Ahi tienen que salir
NO-VERIFICABLE, no verde.
"""

__all__ = ['HttpChecksTest']

import argparse
import os
import shutil
import tempfile
import unittest

import contexto

H = contexto.instrumento('http_checks')


def _opts(**kwargs):
    base = dict(exige=None)
    base.update(kwargs)
    return argparse.Namespace(**base)


PAGINA = '<html><body><div id="lista">todo</div></body></html>'
FRAGMENTO = '<div id="lista">solo el fragmento</div>'


def _captura(metodo, ruta, hx, estado, cabeceras, cuerpo):
    lineas = ['{} {}'.format(metodo, ruta)]
    if hx is not None:
        lineas.append('HX-Request: {}'.format(hx))
    lineas.append('')
    lineas.append(str(estado))
    lineas.extend('{}: {}'.format(k, v) for k, v in cabeceras.items())
    lineas.append('')
    lineas.append(cuerpo)
    return '\n'.join(lineas)


class HttpChecksTest(unittest.TestCase):
    """Cada regla de HTTP contra capturas rojas y verdes."""

    def setUp(self):
        """SetUp."""
        self.raiz = tempfile.mkdtemp(prefix='kddbook-http-')
        self.addCleanup(shutil.rmtree, self.raiz, True)

    def _dir(self, nombre, archivos):
        ruta = os.path.join(self.raiz, nombre)
        os.makedirs(ruta, exist_ok=True)
        for archivo, contenido in archivos.items():
            with open(os.path.join(ruta, archivo), 'w', encoding='utf-8',
                      newline='\n') as fh:
                fh.write(contenido)
        return H.capturas([ruta])

    def test_todas_las_reglas_tienen_prueba(self):
        """Todas las reglas tienen prueba."""
        probadas = {n.split('_')[1] for n in dir(self) if n.startswith('test_')}
        self.assertEqual(set(H.RULES) - probadas, set(),
                         'hay reglas de HTTP sin prueba')

    # --------------------------------------------------------------- vary
    def test_vary_detecta_y_acepta(self):
        """Las dos mitades de `vary`: dispara sobre el caso roto y calla
        sobre el sano. Con una sola, un instrumento que nunca dispara
        pasaria igual.
        """
        base = {'Content-Type': 'text/html'}
        rojo = self._dir('varyr', {
            'pagina.http': _captura('GET', '/lista', None, 200, base, PAGINA),
            'fragmento.http': _captura('GET', '/lista', 'true', 200, base, FRAGMENTO)})
        hallazgos = H.check_vary(rojo, _opts())
        self.assertTrue(hallazgos, 'la respuesta varia y no lo declara')
        self.assertIn('Vary', hallazgos[0][0])

        con_vary = dict(base, **{'Vary': 'HX-Request'})
        verde = self._dir('varyv', {
            'pagina.http': _captura('GET', '/lista', None, 200, base, PAGINA),
            'fragmento.http': _captura('GET', '/lista', 'true', 200, con_vary, FRAGMENTO)})
        self.assertEqual(H.check_vary(verde, _opts()), [])

    def test_vary_no_exige_nada_si_la_respuesta_no_varia(self):
        """Declarar Vary cuando el cuerpo es el mismo seria pedir ruido."""
        base = {'Content-Type': 'text/html'}
        igual = self._dir('varyi', {
            'a.http': _captura('GET', '/estatico', None, 200, base, PAGINA),
            'b.http': _captura('GET', '/estatico', 'true', 200, base, PAGINA)})
        self.assertEqual(H.check_vary(igual, _opts()), [])

    def test_vary_avisa_si_no_hay_con_que_comparar(self):
        """Con una sola captura no se puede demostrar que la respuesta varia."""
        sola = self._dir('varys', {
            'a.http': _captura('GET', '/lista', 'true', 200,
                               {'Content-Type': 'text/html'}, FRAGMENTO)})
        with self.assertRaises(H.NoVerificable):
            H.check_vary(sola, _opts())

    # ---------------------------------------------------------------- csp
    def test_csp_detecta_y_acepta(self):
        """Las dos mitades de `csp`: dispara sobre el caso roto y calla
        sobre el sano. Con una sola, un instrumento que nunca dispara
        pasaria igual.
        """
        cab = {'Content-Type': 'text/html',
               'Content-Security-Policy': "default-src 'self'; connect-src 'self'"}
        verde = self._dir('cspv', {'a.http': _captura('GET', '/', None, 200, cab, PAGINA)})
        self.assertEqual(
            H.check_csp(verde, _opts(exige=['default-src', 'connect-src'])), [])

        sin = self._dir('cspr', {'a.http': _captura('GET', '/', None, 200,
                                                    {'Content-Type': 'text/html'}, PAGINA)})
        self.assertTrue(H.check_csp(sin, _opts(exige=['default-src'])),
                        'no detecto la respuesta HTML sin politica')

    def test_csp_detecta_la_politica_incompleta(self):
        """Una politica vacia tambien es una CSP: por eso se exigen directivas."""
        cab = {'Content-Type': 'text/html', 'Content-Security-Policy': "default-src 'self'"}
        parcial = self._dir('cspp', {'a.http': _captura('GET', '/', None, 200, cab, PAGINA)})
        hallazgos = H.check_csp(parcial, _opts(exige=['default-src', 'connect-src']))
        self.assertTrue(hallazgos)
        self.assertIn('connect-src', hallazgos[0][0])

    def test_csp_acepta_el_meta_que_muestra_la_doc(self):
        """Csp acepta el meta que muestra la doc."""
        cuerpo = ('<html><head><meta http-equiv="Content-Security-Policy" '
                  'content="default-src \'self\'"></head><body>x</body></html>')
        meta = self._dir('cspm', {'a.http': _captura('GET', '/', None, 200,
                                                     {'Content-Type': 'text/html'}, cuerpo)})
        self.assertEqual(H.check_csp(meta, _opts(exige=['default-src'])), [])

    def test_csp_ignora_lo_que_no_es_html(self):
        """Csp ignora lo que no es html."""
        cab = {'Content-Type': 'application/json'}
        json_ = self._dir('cspj', {'a.http': _captura('GET', '/api', None, 200, cab, '{}')})
        self.assertEqual(H.check_csp(json_, _opts(exige=['default-src'])), [])

    def test_csp_avisa_si_no_se_declaran_directivas(self):
        """Csp avisa si no se declaran directivas."""
        cab = {'Content-Type': 'text/html'}
        alguna = self._dir('cspn', {'a.http': _captura('GET', '/', None, 200, cab, PAGINA)})
        with self.assertRaises(H.NoVerificable):
            H.check_csp(alguna, _opts())

    # ------------------------------------------------------------ formato
    def test_una_captura_mal_formada_no_da_verde(self):
        """Una captura mal formada no da verde."""
        ruta = os.path.join(self.raiz, 'mala')
        os.makedirs(ruta)
        with open(os.path.join(ruta, 'x.http'), 'w', encoding='utf-8') as fh:
            fh.write('esto no es una captura')
        with self.assertRaises(H.NoVerificable):
            H.capturas([ruta])


if __name__ == '__main__':
    unittest.main()
