"""Cada instrumento contra un caso rojo y uno verde.

Un instrumento que nunca dispara pasa todos los gates y no mide nada, que es
exactamente el fallo silencioso que este pipeline existe para evitar. Por eso
cada regla necesita las dos pruebas: que detecte lo que dice detectar, y que no
grite sobre codigo conforme.
"""

import ast
import unittest

import contexto

checks = contexto.instrumento('checks')


# (regla, limite, fuente_roja, fuente_verde)
CASOS = [
    ('anatomia', 0,
     'import unittest\n\n\nclass T(unittest.TestCase):\n'
     '    def test_nada(self):\n        resultado = 1 + 1\n        print(resultado)\n',
     'import unittest\n\n\nclass T(unittest.TestCase):\n'
     '    def test_suma(self):\n        self.assertEqual(1 + 1, 2)\n'),

    ('exprops', 3,
     'def decidir(a, b, c, d):\n'
     '    return (a and b) or (c and d) or (a > b) or (c < d)\n',
     'def decidir(a, b):\n    return a and b\n'),

    ('j2', 0,
     'class Config:\n    TOPE = 100\n    MINIMO = 1\n\n\n'
     'class Servicio(Config):\n    def usar(self):\n        return self.TOPE\n',
     'class Config:\n    TOPE = 100\n    MINIMO = 1\n\n\n'
     'class Servicio:\n    def usar(self):\n        return Config.TOPE\n'),

    ('metlineas', 5,
     'def larga(n):\n' + ''.join('    n += {}\n'.format(i) for i in range(8))
     + '    return n\n',
     'def corta(n):\n    return n + 1\n'),

    ('c5', 0,
     '# resultado = calcular(3, 4)\nvalor = 1\n',
     '# el impuesto se aplica sobre el neto\nvalor = 1\n'),

    ('f2', 0,
     'def agregar(items):\n    items.append(1)\n    return items\n',
     'def agregar(items):\n    return items + [1]\n'),

    ('f3', 0,
     'def render(texto, en_mayusculas=False):\n'
     '    if en_mayusculas:\n        return texto.upper()\n    return texto\n',
     'def render(texto):\n    return texto\n'),

    ('g4', 0,
     'import os  # noqa\n',
     'import os\nprint(os.sep)\n'),

    ('g5', 0,
     'def a():\n    x = 1\n    y = 2\n    return x + y\n'
     'def b():\n    x = 1\n    y = 2\n    return x + y\n',
     'def a():\n    x = 1\n    return x\n'),

    ('g7', 0,
     'class Base:\n    def crear(self):\n        return Hija()\n'
     'class Hija(Base):\n    pass\n',
     'class Base:\n    def crear(self):\n        return None\n'
     'class Hija(Base):\n    pass\n'),

    ('g8', 2,
     'class Ancha:\n' + ''.join(
         '    def m{}(self):\n        return {}\n'.format(i, i) for i in range(4)),
     'class Angosta:\n    def uno(self):\n        return 1\n'),

    ('g9', 0,
     "__all__ = ['viva']\ndef muerta():\n    return 1\ndef viva():\n    return 2\n",
     "__all__ = ['viva']\ndef viva():\n    return 2\n"),

    ('g10', 2,
     'def f(bandera):\n    total = 0\n'
     '    if bandera:\n        pass\n    if bandera:\n        pass\n'
     '    if bandera:\n        pass\n    return total\n',
     'def f():\n    total = 0\n    return total\n'),

    ('g12', 0,
     'import os\nvalor = 1\n',
     'import os\nprint(os.sep)\n'),

    ('g14', 1,
     'class Calculadora:\n    def pagar(self, empleado):\n'
     '        tarifa = empleado.tarifa\n        horas = empleado.horas\n'
     '        extra = empleado.extra\n        return tarifa * horas + extra\n',
     'class Calculadora:\n    def pagar(self):\n'
     '        return self.tarifa * self.horas + self.extra\n'),

    ('g23', 2,
     'def area(figura):\n'
     '    if figura.tipo == "circulo":\n        return 1\n'
     '    elif figura.tipo == "cuadrado":\n        return 2\n'
     '    elif figura.tipo == "triangulo":\n        return 3\n'
     '    return 0\n',
     'def area(figura):\n    return figura.area()\n'),

    ('g25', 0,
     'def espera():\n    return 3600\n',
     'SEGUNDOS_POR_HORA = 3600\ndef espera():\n    return SEGUNDOS_POR_HORA\n'),

    ('g28', 1,
     'def ok(a, b, c):\n    if a and b and c:\n        return 1\n    return 0\n',
     'def ok(a):\n    if a:\n        return 1\n    return 0\n'),

    ('g29', 0,
     'def cobrar(saldo):\n    if not saldo:\n        return 0\n    return saldo\n',
     'def cobrar(saldo):\n    if saldo:\n        return saldo\n    return 0\n'),

    ('g33', 0,
     'def f(nivel, otro, mas):\n    a = nivel + 1\n    b = nivel + 1\n'
     '    c = nivel + 1\n    return a + b + c\n',
     'def f(nivel):\n    siguiente = nivel + 1\n    return siguiente\n'),

    ('n5', 0,
     'def procesar(datos):\n    x = 0\n    for d in datos:\n        x += d\n'
     '    if x:\n        x -= 1\n    if datos:\n        x += 2\n    return x\n',
     'def procesar(datos):\n    x = len(datos)\n    return x\n'),

    ('n6', 0,
     'def f():\n    m_valor = 1\n    return m_valor\n',
     'def f():\n    valor = 1\n    return valor\n'),
]


class InstrumentosTest(unittest.TestCase):

    def _correr(self, rule, source, limit):
        func = checks.RULES[rule][0]
        return func(ast.parse(source), source, limit)

    def test_todas_las_reglas_estan_cubiertas(self):
        cubiertas = {caso[0] for caso in CASOS}
        self.assertEqual(cubiertas, set(checks.RULES),
                         'hay reglas registradas sin caso de prueba')

    def test_ningun_check_queda_sin_registrar(self):
        """Un check escrito pero ausente de RULES es codigo muerto que no mide.

        Comparar CASOS contra RULES no lo detecta: si la regla no esta en
        ninguno de los dos, ambos conjuntos coinciden y el agujero pasa. Hay
        que mirar las funciones del modulo, que es la fuente de verdad.
        """
        definidos = {name[len('check_'):] for name in dir(checks)
                     if name.startswith('check_')}
        registrados = set(checks.RULES) | set(checks.ALIASES.values())
        self.assertEqual(definidos - registrados, set(),
                         'hay checks definidos que no estan en RULES: no miden nada')

    def test_los_alias_apuntan_a_reglas_reales(self):
        for alias, destino in checks.ALIASES.items():
            self.assertIn(destino, checks.RULES,
                          'el alias {} apunta a {} que no existe'.format(alias, destino))

    def test_g9_avisa_cuando_no_puede_verificar(self):
        """Sin `__all__` no se puede saber que es API y que es codigo muerto.

        Lo importante es que no devuelva lista vacia: eso se leeria como
        "esta limpio" cuando en realidad es "no puedo saber".
        """
        with self.assertRaises(checks.NoVerificable):
            self._correr('g9', 'def sola():\n    return 1\n', 0)

    def test_rojo_dispara(self):
        for rule, limit, rojo, _verde in CASOS:
            with self.subTest(regla=rule):
                self.assertTrue(self._correr(rule, rojo, limit),
                                'la regla {} no detecto su propio caso rojo'.format(rule))

    def test_verde_no_dispara(self):
        for rule, limit, _rojo, verde in CASOS:
            with self.subTest(regla=rule):
                self.assertEqual(self._correr(rule, verde, limit), [],
                                 'la regla {} grito sobre codigo conforme'.format(rule))

    def test_g4_no_confunde_nombrar_un_marcador_con_usarlo(self):
        """Un marcador adentro de una cadena es texto, no una supresion.

        Regresion: la primera version leia lineas crudas y por eso `checks.py`
        se marcaba a si mismo — la expresion regular que define los marcadores
        contiene los marcadores. Es el mismo defecto que `daemonizar` tuvo con
        `.pid`: confundir nombrar algo con hacerlo.
        """
        patron = 'MARCADORES = "@SuppressWarnings|# noqa"\n'
        self.assertEqual(self._correr('g4', patron, 0),
                         [], 'tomo por supresion un marcador que esta en una cadena')
        self.assertTrue(self._correr('g4', 'import os  # noqa\n', 0),
                        'una supresion de verdad sigue siendo un hallazgo')

    def test_g12_perdona_el_import_marcado_con_noqa(self):
        """Un import por su efecto no usa el nombre nunca: `# noqa` lo declara.

        Aparecio arreglando este repositorio: las suites pasaron a importar un
        modulo `contexto` que arma el camino de busqueda, y g12 las marcaba a
        las doce. Sin manera de declarar la excepcion, el instrumento obliga a
        elegir entre dos rojos.
        """
        self.assertTrue(self._correr('g12', 'import os\n', 0),
                        'un import sin usar y sin marcar sigue siendo desorden')
        self.assertEqual(self._correr('g12', 'import os  # noqa: F401\n', 0), [],
                         'el import marcado a proposito no es desorden')


if __name__ == '__main__':
    unittest.main()
