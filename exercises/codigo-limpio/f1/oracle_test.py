"""Oraculo congelado del ejercicio F1.

A diferencia de G36, esta heuristica cambia la interfaz: reducir argumentos
obliga a agrupar. Por eso el oraculo esta escrito contra la firma de destino
(`crear_evento(datos)`) y el seed lo pone en rojo. El instrumento sigue
haciendo falta: sin el, nada impide "aprobar" el oraculo con una firma de
cuatro argumentos.
"""

import unittest

from target import crear_evento

DATOS = {
    'nombre': 'KDD en la practica',
    'fecha': '2026-09-14',
    'ciudad': 'Rosario',
    'capacidad': 40,
    'precio': 120,
}


class CrearEventoTest(unittest.TestCase):

    def test_copia_los_campos_tal_cual(self):
        evento = crear_evento(dict(DATOS))
        for clave, valor in DATOS.items():
            self.assertEqual(evento[clave], valor)

    def test_agotado_es_falso_con_capacidad_disponible(self):
        self.assertIs(crear_evento(dict(DATOS))['agotado'], False)

    def test_agotado_es_verdadero_con_capacidad_cero(self):
        datos = dict(DATOS, capacidad=0)
        self.assertIs(crear_evento(datos)['agotado'], True)

    def test_no_agrega_ni_omite_claves(self):
        evento = crear_evento(dict(DATOS))
        self.assertEqual(sorted(evento), sorted(list(DATOS) + ['agotado']))

    def test_no_muta_la_entrada(self):
        datos = dict(DATOS)
        crear_evento(datos)
        self.assertEqual(datos, DATOS)

    def test_capacidad_negativa_no_cuenta_como_agotado(self):
        self.assertIs(crear_evento(dict(DATOS, capacidad=-1))['agotado'], False)


if __name__ == '__main__':
    unittest.main()
