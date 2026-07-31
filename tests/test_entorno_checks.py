"""Los instrumentos de entorno contra proyectos rojos y verdes.

Cada regla sale de una afirmacion del manifiesto que se puede contradecir, y la
prueba arma el proyecto minimo que la contradice. Las dos que dependen de una
declaracion —el manifiesto de dependencias y los despliegues— traen ademas el
caso en que falta: ahi tienen que salir NO-VERIFICABLE y no verde.
"""

__all__ = ['EntornoChecksTest']

import argparse
import os
import shutil
import tempfile
import unittest

import contexto

E = contexto.instrumento('entorno_checks')


class EntornoChecksTest(unittest.TestCase):
    """Cada regla de entorno contra un proyecto roto y uno sano."""

    def setUp(self):
        """SetUp."""
        self.raiz = tempfile.mkdtemp(prefix='kddbook-ent-')
        self.addCleanup(shutil.rmtree, self.raiz, True)

    def _proyecto(self, archivos):
        for nombre, contenido in archivos.items():
            ruta = os.path.join(self.raiz, nombre.replace('/', os.sep))
            os.makedirs(os.path.dirname(ruta), exist_ok=True)
            with open(ruta, 'w', encoding='utf-8', newline='\n') as fh:
                fh.write(contenido)
        return self.raiz

    def _opts(self, **kwargs):
        base = dict(proyecto=self.raiz, manifiesto=None, despliegue=[], nombre=[])
        base.update(kwargs)
        return argparse.Namespace(**base)

    def _correr(self, regla, archivos, **kwargs):
        self._proyecto(archivos)
        return E.RULES[regla][0](E._fuentes(self.raiz), self._opts(**kwargs))

    def test_todas_las_reglas_tienen_prueba(self):
        """Todas las reglas tienen prueba."""
        probadas = {n.split('_')[1] for n in dir(self) if n.startswith('test_')}
        self.assertEqual(set(E.RULES) - probadas, set(),
                         'hay reglas de entorno sin prueba')

    def test_todas_las_funciones_check_estan_registradas(self):
        """Todas las funciones check estan registradas."""
        definidas = {n[len('check_'):] for n in dir(E) if n.startswith('check_')}
        self.assertEqual(definidas - set(E.RULES), set(),
                         'hay checks escritos que el instrumento no puede ejecutar')

    # -------------------------------------------------------- dependencias
    def test_dependencias_detecta_y_acepta(self):
        """Las dos mitades de `dependencias`: dispara sobre el caso roto y calla
        sobre el sano. Con una sola, un instrumento que nunca dispara
        pasaria igual.
        """
        rojo = self._correr('dependencias',
                            {'app.py': 'import os\nimport requests\n',
                             'requirements.txt': 'flask==3.0\n'},
                            manifiesto='requirements.txt')
        self.assertTrue(rojo, 'no detecto el import que no esta declarado')
        self.assertIn('requests', rojo[0][2])

        verde = self._correr('dependencias',
                             {'app.py': 'import os\nimport requests\n',
                              'requirements.txt': 'requests>=2.0\n'},
                             manifiesto='requirements.txt')
        self.assertEqual(verde, [])

    def test_dependencias_no_marca_la_stdlib_ni_lo_local(self):
        """Dependencias no marca la stdlib ni lo local."""
        verde = self._correr('dependencias',
                             {'app.py': 'import json\nimport util\nfrom . import x\n',
                              'util.py': 'X = 1\n',
                              'requirements.txt': '\n'},
                             manifiesto='requirements.txt')
        self.assertEqual(verde, [], 'marco stdlib, un modulo local o un import relativo')

    def test_dependencias_sin_manifiesto_declarado_no_mide(self):
        """Dependencias sin manifiesto declarado no mide."""
        with self.assertRaises(E.NoVerificable):
            self._correr('dependencias', {'app.py': 'import requests\n'})

    def test_dependencias_con_manifiesto_inexistente_es_rojo(self):
        """No declarar nada no es una duda: es exactamente lo que el factor prohibe."""
        rojo = self._correr('dependencias', {'app.py': 'import requests\n'},
                            manifiesto='requirements.txt')
        self.assertTrue(rojo)
        self.assertIn('no existe', rojo[0][2])

    # --------------------------------------------------------------- config
    def test_config_detecta_y_acepta(self):
        """Las dos mitades de `config`: dispara sobre el caso roto y calla
        sobre el sano. Con una sola, un instrumento que nunca dispara
        pasaria igual.
        """
        rojo = self._correr('config', {'app.py': 'API_KEY = "sk-abc123"\n'})
        self.assertTrue(rojo, 'no detecto la credencial escrita en el codigo')

        verde = self._correr('config',
                             {'app.py': 'import os\nAPI_KEY = os.environ["API_KEY"]\n'})
        self.assertEqual(verde, [], 'marco una lectura del entorno')

    def test_config_ignora_el_placeholder_vacio(self):
        """`TOKEN = ""` es justo lo que deja quien ya saco la clave."""
        self.assertEqual(self._correr('config', {'app.py': 'TOKEN = ""\n'}), [])

    def test_config_acepta_nombres_declarados_por_el_proyecto(self):
        """Config acepta nombres declarados por el proyecto."""
        self.assertEqual(self._correr('config', {'app.py': 'PEPE = "x"\n'}), [])
        self.assertTrue(self._correr('config', {'app.py': 'PEPE = "x"\n'}, nombre=['pepe']))

    # ------------------------------------------------------------ servicios
    def test_servicios_detecta_y_acepta(self):
        """Las dos mitades de `servicios`: dispara sobre el caso roto y calla
        sobre el sano. Con una sola, un instrumento que nunca dispara
        pasaria igual.
        """
        rojo = self._correr('servicios',
                            {'app.py': 'DB = "postgres://u:p@localhost/db"\n'})
        self.assertTrue(rojo, 'no detecto el locator escrito en el codigo')

        verde = self._correr('servicios',
                             {'app.py': 'import os\nDB = os.environ["DATABASE_URL"]\n'})
        self.assertEqual(verde, [])

    def test_servicios_mira_la_forma_del_valor_y_no_el_nombre(self):
        """Es lo que la separa de `config`: ahi importa como se llama, aca que es."""
        self.assertTrue(self._correr('servicios', {'app.py': 'x = "redis://h:6379"\n'}))

    # --------------------------------------------------------------- puerto
    def test_puerto_detecta_y_acepta(self):
        """Las dos mitades de `puerto`: dispara sobre el caso roto y calla
        sobre el sano. Con una sola, un instrumento que nunca dispara
        pasaria igual.
        """
        verde = self._correr('puerto',
                             {'app.py': 'import socket\ns = socket.socket()\n'
                                        's.bind(("0.0.0.0", 8000))\n'})
        self.assertEqual(verde, [])

        rojo = self._correr('puerto', {'app.py': 'def application(env, start):\n'
                                                 '    return [b"hola"]\n'})
        self.assertTrue(rojo, 'no detecto que la app depende de un servidor inyectado')

    # -------------------------------------------------------------- paridad
    def test_paridad_detecta_y_acepta(self):
        """Las dos mitades de `paridad`: dispara sobre el caso roto y calla
        sobre el sano. Con una sola, un instrumento que nunca dispara
        pasaria igual.
        """
        archivos = {'app.py': 'X = 1\n',
                    'dev.yml': 'services:\n  db:\n    image: postgres:14\n',
                    'prod.yml': 'services:\n  db:\n    image: postgres:16\n'}
        rojo = self._correr('paridad', archivos,
                            despliegue=['dev=dev.yml', 'prod=prod.yml'])
        self.assertTrue(rojo, 'no detecto la diferencia de version')
        self.assertIn('postgres', rojo[0][2])

        archivos['prod.yml'] = 'services:\n  db:\n    image: postgres:14\n'
        self.assertEqual(self._correr('paridad', archivos,
                                      despliegue=['dev=dev.yml', 'prod=prod.yml']), [])

    def test_paridad_detecta_el_servicio_que_falta_en_un_despliegue(self):
        """Paridad detecta el servicio que falta en un despliegue."""
        rojo = self._correr('paridad',
                            {'app.py': 'X = 1\n',
                             'dev.yml': 'image: postgres:14\nimage: redis:7\n',
                             'prod.yml': 'image: postgres:14\n'},
                            despliegue=['dev=dev.yml', 'prod=prod.yml'])
        self.assertTrue(any('redis' in d for _r, _l, d in rojo))

    def test_paridad_con_un_solo_despliegue_no_mide(self):
        """Con uno solo, "coinciden" seria una afirmacion sobre un conjunto de uno."""
        with self.assertRaises(E.NoVerificable):
            self._correr('paridad',
                         {'app.py': 'X = 1\n', 'dev.yml': 'image: postgres:14\n'},
                         despliegue=['dev=dev.yml'])

    def test_paridad_avisa_si_el_despliegue_no_declara_imagenes(self):
        """Paridad avisa si el despliegue no declara imagenes."""
        with self.assertRaises(E.NoVerificable):
            self._correr('paridad',
                         {'app.py': 'X = 1\n', 'a.yml': 'nada: aca\n',
                          'b.yml': 'image: postgres:14\n'},
                         despliegue=['a=a.yml', 'b=b.yml'])

    # ----------------------------------------------------------- daemonizar
    def test_daemonizar_detecta_y_acepta(self):
        """Las dos mitades de `daemonizar`: dispara sobre el caso roto y calla
        sobre el sano. Con una sola, un instrumento que nunca dispara
        pasaria igual.
        """
        self.assertTrue(self._correr('daemonizar', {'app.py': 'import os\nos.fork()\n'}))
        self.assertEqual(self._correr('daemonizar', {'app.py': 'print("hola")\n'}), [])

    def test_daemonizar_detecta_el_archivo_pid(self):
        """Daemonizar detecta el archivo pid."""
        rojo = self._correr('daemonizar', {'app.py': 'open("/var/run/app.pid", "w")\n'})
        self.assertTrue(rojo, 'no detecto la escritura del archivo PID')

    def test_daemonizar_no_confunde_preguntar_con_escribir(self):
        """Regresion: `ruta.endswith('.pid')` no escribe ningun archivo PID.

        La primera version marcaba cualquier llamada con un argumento terminado
        en `.pid`, asi que la linea que hace la comprobacion se marcaba a si
        misma. Lo encontro el instrumento corrido sobre este repositorio, no
        esta prueba: la prueba existe para que no vuelva.
        """
        verde = self._correr('daemonizar',
                             {'app.py': 'def es_pid(ruta):\n'
                                        '    return ruta.endswith(".pid")\n'})
        self.assertEqual(verde, [], 'marco en rojo una comprobacion, no una escritura')

    # -------------------------------------------------------------- sigterm
    def test_sigterm_detecta_y_acepta(self):
        """Las dos mitades de `sigterm`: dispara sobre el caso roto y calla
        sobre el sano. Con una sola, un instrumento que nunca dispara
        pasaria igual.
        """
        verde = self._correr('sigterm',
                             {'app.py': 'import signal\n'
                                        'signal.signal(signal.SIGTERM, lambda *a: None)\n'})
        self.assertEqual(verde, [])
        self.assertTrue(self._correr('sigterm', {'app.py': 'print("hola")\n'}))

    def test_sigterm_no_se_conforma_con_cualquier_senial(self):
        """Sigterm no se conforma con cualquier senial."""
        rojo = self._correr('sigterm',
                            {'app.py': 'import signal\n'
                                       'signal.signal(signal.SIGINT, lambda *a: None)\n'})
        self.assertTrue(rojo, 'acepto SIGINT como si fuera SIGTERM')

    # ----------------------------------------------------------------- logs
    def test_logs_detecta_y_acepta(self):
        """Las dos mitades de `logs`: dispara sobre el caso roto y calla
        sobre el sano. Con una sola, un instrumento que nunca dispara
        pasaria igual.
        """
        rojo = self._correr('logs', {'app.py': 'import logging\n'
                                               'h = logging.FileHandler("app.log")\n'})
        self.assertTrue(rojo, 'no detecto el handler a archivo')
        self.assertEqual(self._correr('logs', {'app.py': 'import logging\n'
                                                         'logging.basicConfig()\n'}), [])

    def test_logs_detecta_el_basicconfig_con_filename(self):
        """Logs detecta el basicconfig con filename."""
        rojo = self._correr('logs', {'app.py': 'import logging\n'
                                               'logging.basicConfig(filename="a.log")\n'})
        self.assertTrue(rojo)

    # ------------------------------------------------------------- alcance
    def test_las_pruebas_del_proyecto_medido_no_cuentan(self):
        """Un locator de mentira en un fixture es lo que un fixture debe tener.

        Vale para todas las reglas porque el filtro esta en `_fuentes`, y por
        eso se comprueba una vez y sobre la regla mas propensa a marcarlo.
        """
        verde = self._correr('servicios',
                             {'app.py': 'X = 1\n',
                              'test_app.py': 'DB = "postgres://u:p@localhost/db"\n',
                              'tests/conftest.py': 'DB = "redis://x"\n'})
        self.assertEqual(verde, [])


if __name__ == '__main__':
    unittest.main()
