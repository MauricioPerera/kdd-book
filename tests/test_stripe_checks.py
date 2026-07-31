"""Los instrumentos de stripe contra proyectos rojos y verdes.

Dos reglas, cada una la contrapositiva de una prohibicion sin condicional
del propio texto de docs.stripe.com/api: la prueba arma el proyecto minimo
que la contradice y el minimo que la respeta.
"""

__all__ = ['StripeChecksTest']

import argparse
import os
import shutil
import tempfile
import unittest

import contexto

S = contexto.instrumento('stripe_checks')


class StripeChecksTest(unittest.TestCase):
    """Cada regla de stripe contra un proyecto roto y uno sano."""

    def setUp(self):
        """SetUp."""
        self.raiz = tempfile.mkdtemp(prefix='kddbook-stripe-')
        self.addCleanup(shutil.rmtree, self.raiz, True)

    def _proyecto(self, archivos):
        for nombre, contenido in archivos.items():
            ruta = os.path.join(self.raiz, nombre.replace('/', os.sep))
            os.makedirs(os.path.dirname(ruta), exist_ok=True)
            with open(ruta, 'w', encoding='utf-8', newline='\n') as fh:
                fh.write(contenido)
        return self.raiz

    def _opts(self, **kwargs):
        base = dict(proyecto=self.raiz)
        base.update(kwargs)
        return argparse.Namespace(**base)

    def _correr(self, regla, archivos, **kwargs):
        self._proyecto(archivos)
        return S.RULES[regla][0](S._fuentes(self.raiz), self._opts(**kwargs))

    def test_todas_las_reglas_tienen_prueba(self):
        """Todas las reglas tienen prueba."""
        metodos = [n for n in dir(self) if n.startswith('test_')]
        sin_prueba = [r for r in S.RULES
                     if not any(m.startswith('test_' + r.replace('-', '_'))
                                for m in metodos)]
        self.assertEqual(sin_prueba, [], 'hay reglas de stripe sin prueba')

    def test_todas_las_funciones_check_estan_registradas(self):
        """Todas las funciones check estan registradas."""
        definidas = {n[len('check_'):].replace('_', '-') for n in dir(S)
                    if n.startswith('check_')}
        self.assertEqual(definidas - set(S.RULES), set(),
                         'hay checks escritos que el instrumento no puede ejecutar')

    # ------------------------------------------------------- claves-en-codigo
    def test_claves_en_codigo_detecta_y_acepta(self):
        """Las dos mitades de `claves-en-codigo`: dispara sobre el caso roto
        y calla sobre el sano. Con una sola, un instrumento que nunca dispara
        pasaria igual.
        """
        rojo = self._correr('claves-en-codigo',
                            {'app.py': 'STRIPE_KEY = "sk_test_EXAMPLEFAKEKEY01"\n'})
        self.assertTrue(rojo, 'no detecto la clave secreta embebida en el codigo')
        self.assertIn('sk_test_', rojo[0][2])

        verde = self._correr('claves-en-codigo',
                             {'app.py': 'import os\n'
                                        'STRIPE_KEY = os.environ["STRIPE_KEY"]\n'})
        self.assertEqual(verde, [], 'marco una lectura del entorno')

    def test_claves_en_codigo_detecta_la_restringida_live(self):
        """Detecta tambien una clave restringida en modo live, no solo secretas de test."""
        rojo = self._correr('claves-en-codigo',
                            {'app.py': 'KEY = "rk_live_ABCDEFGHIJKLMNOPQRST"\n'})
        self.assertTrue(rojo, 'no detecto la clave restringida live')

    def test_claves_en_codigo_no_marca_la_publicable(self):
        """Las publicables (`pk_`) estan pensadas para vivir en el cliente."""
        verde = self._correr('claves-en-codigo',
                             {'app.py': 'PK = "pk_live_ABCDEFGHIJKLMNOPQRST"\n'})
        self.assertEqual(verde, [], 'marco una clave publicable como si fuera secreta')

    # ------------------------------------------------- idempotencia-en-lectura
    def test_idempotencia_en_lectura_detecta_y_acepta(self):
        """Las dos mitades de `idempotencia-en-lectura`: dispara sobre el
        caso roto y calla sobre el sano. Con una sola, un instrumento que
        nunca dispara pasaria igual.
        """
        rojo = self._correr('idempotencia-en-lectura',
                            {'app.py': 'requests.get(url, '
                                       'headers={"Idempotency-Key": k})\n'})
        self.assertTrue(rojo, 'no detecto el header de idempotencia en un GET')

        verde = self._correr('idempotencia-en-lectura',
                             {'app.py': 'requests.get(url, headers={"Accept": "json"})\n'})
        self.assertEqual(verde, [])

    def test_idempotencia_en_lectura_detecta_el_delete(self):
        """La misma prohibicion vale para DELETE, no solo para GET."""
        rojo = self._correr('idempotencia-en-lectura',
                            {'app.py': 'requests.delete(url, '
                                       'headers={"Idempotency-Key": k})\n'})
        self.assertTrue(rojo, 'no detecto el header de idempotencia en un DELETE')

    def test_idempotencia_en_lectura_no_marca_el_post(self):
        """En POST el header es valido: la regla es solo sobre GET y DELETE."""
        verde = self._correr('idempotencia-en-lectura',
                             {'app.py': 'requests.post(url, '
                                        'headers={"Idempotency-Key": k})\n'})
        self.assertEqual(verde, [], 'marco un POST, donde el header si tiene efecto')

    # ------------------------------------------------------------- alcance
    def test_las_pruebas_del_proyecto_medido_no_cuentan(self):
        """Una clave de mentira en un fixture es lo que un fixture debe tener."""
        verde = self._correr('claves-en-codigo',
                             {'app.py': 'X = 1\n',
                              'test_app.py':
                                  'K = "sk_test_EXAMPLEFAKEKEY01"\n'})
        self.assertEqual(verde, [])


if __name__ == '__main__':
    unittest.main()
