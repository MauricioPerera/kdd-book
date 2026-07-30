"""La memoria portable: exportar, consultar y fusionar.

La prueba que importa es la fusion, porque es lo que los ids estables
habilitan. Si el id fuera un resumen del titulo, la misma tecnica de dos
ediciones tendria dos ids y la fusion produciria duplicados en vez de una
entrada mas rica — y peor, los desacuerdos de triaje entre las dos fuentes
nunca se verian, porque nada las estaria comparando.
"""

import os
import sys
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

import memoria as M  # noqa: E402


def _tecnica(tid, titulo, pila='A', verification='instrumented',
             instrumento='checks.py --rule g5', alias=None, enlaces=None):
    return {'id': tid, 'libro': tid.split('/')[0], 'titulo': titulo,
            'pila': pila, 'verification': verification,
            'instrumento': instrumento, 'umbral': None, 'por_que_no': None,
            'locator': 'cap 17', 'alias': list(alias or []), 'tags': [],
            'enlaces': list(enlaces or []), 'contrato': None}


def _memoria(tecnicas, libros=None):
    return {'formato': 'kdd-book/memoria', 'version': 1,
            'libros': libros or [{'slug': 'codigo-limpio', 'titulo': 'Codigo Limpio'}],
            'instrumentos': [], 'tecnicas': tecnicas}


class FusionTest(unittest.TestCase):

    def test_la_misma_tecnica_de_dos_ediciones_es_una_sola(self):
        es = _memoria([_tecnica('codigo-limpio/g36', 'G36: Evitar desplazamientos transitivos',
                                alias=['ley de Demeter'])])
        en = _memoria([_tecnica('codigo-limpio/g36', 'G36: Avoid transitive navigation',
                                instrumento=None, alias=['law of Demeter'])])
        fusion, conflictos = M.fusionar([es, en])
        self.assertEqual(len(fusion['tecnicas']), 1, 'se duplico en vez de fusionarse')
        self.assertEqual(conflictos, [])

    def test_el_titulo_de_la_otra_edicion_queda_como_alias(self):
        es = _memoria([_tecnica('codigo-limpio/g36', 'Evitar desplazamientos transitivos')])
        en = _memoria([_tecnica('codigo-limpio/g36', 'Avoid transitive navigation')])
        fusion, _ = M.fusionar([es, en])
        alias = fusion['tecnicas'][0]['alias']
        self.assertIn('Avoid transitive navigation', alias,
                      'un titulo en otro idioma es un nombre alternativo')

    def test_completa_el_instrumento_que_a_una_le_falta(self):
        con = _memoria([_tecnica('codigo-limpio/g5', 'Duplicacion',
                                 instrumento='checks.py --rule g5')])
        sin = _memoria([_tecnica('codigo-limpio/g5', 'Duplication', instrumento=None)])
        fusion, conflictos = M.fusionar([sin, con])
        self.assertEqual(fusion['tecnicas'][0]['instrumento'], 'checks.py --rule g5')
        self.assertEqual(conflictos, [], 'completar un hueco no es un conflicto')

    def test_un_desacuerdo_de_triaje_se_reporta_y_no_se_resuelve(self):
        """Elegir uno en silencio seria inventar un consenso que no existe."""
        mio = _memoria([_tecnica('codigo-limpio/g30', 'Hacer una sola cosa',
                                 pila='B', verification='none', instrumento=None)])
        ajeno = _memoria([_tecnica('codigo-limpio/g30', 'Do one thing',
                                   pila='A', verification='instrumented',
                                   instrumento='lines_max')])
        fusion, conflictos = M.fusionar([mio, ajeno])
        self.assertEqual(len(fusion['tecnicas']), 1)
        campos = {c['campo'] for c in conflictos}
        self.assertIn('pila', campos, 'no reporto el desacuerdo de clasificacion')
        self.assertEqual(fusion['tecnicas'][0]['pila'], 'B',
                         'la primera memoria manda; el desacuerdo va al reporte')

    def test_los_alias_no_se_duplican_por_mayusculas(self):
        a = _memoria([_tecnica('codigo-limpio/g36', 'x', alias=['ley de Demeter'])])
        b = _memoria([_tecnica('codigo-limpio/g36', 'x', alias=['Ley De Demeter'])])
        fusion, _ = M.fusionar([a, b])
        self.assertEqual(fusion['tecnicas'][0]['alias'], ['ley de Demeter'])

    def test_dos_libros_distintos_se_suman(self):
        a = _memoria([_tecnica('codigo-limpio/g5', 'Duplicacion')])
        b = _memoria([_tecnica('scrum-xp/144', 'Codigo duplicado')],
                     libros=[{'slug': 'scrum-xp', 'titulo': 'Scrum y XP'}])
        fusion, _ = M.fusionar([a, b])
        self.assertEqual(len(fusion['tecnicas']), 2)
        self.assertEqual(len(fusion['libros']), 2)

    def test_los_ids_con_prosa_no_se_fusionarian(self):
        """El contraste que justifica la identidad estable.

        Con el esquema viejo —codigo + slug del titulo— la misma tecnica de dos
        ediciones tiene dos ids, asi que se duplica y el desacuerdo de triaje
        entre las dos fuentes no lo ve nadie.
        """
        es = _memoria([_tecnica('codigo-limpio/g36-evitar-desplazamientos-transitivos',
                                'Evitar desplazamientos transitivos', pila='B',
                                verification='none', instrumento=None)])
        en = _memoria([_tecnica('codigo-limpio/g36-avoid-transitive-navigation',
                                'Avoid transitive navigation', pila='A')])
        fusion, conflictos = M.fusionar([es, en])
        self.assertEqual(len(fusion['tecnicas']), 2, 'deberian quedar duplicadas')
        self.assertEqual(conflictos, [], 'y el desacuerdo pasa desapercibido')


class ConsultaTest(unittest.TestCase):

    def test_la_busqueda_ignora_acentos(self):
        m = _memoria([_tecnica('codigo-limpio/g5', 'G5: Duplicación')])
        self.assertEqual(len(M.buscar(m, 'duplicacion')), 1)

    def test_la_busqueda_encuentra_por_nombre_canonico(self):
        """El titulo dice una cosa y el mundo la conoce por otra."""
        m = _memoria([_tecnica('codigo-limpio/g36',
                               'G36: Evitar desplazamientos transitivos',
                               alias=['ley de Demeter', 'law of Demeter'])])
        self.assertEqual(len(M.buscar(m, 'law of demeter')), 1)
        self.assertEqual(len(M.buscar(m, 'demeter')), 1)

    def test_medibles_solo_devuelve_las_que_tienen_instrumento(self):
        m = _memoria([_tecnica('codigo-limpio/g5', 'Duplicacion'),
                      _tecnica('codigo-limpio/g30', 'Una sola cosa', pila='B',
                               verification='none', instrumento=None)])
        self.assertEqual([t['id'] for t in M.medibles(m)], ['codigo-limpio/g5'])


if __name__ == '__main__':
    unittest.main()
