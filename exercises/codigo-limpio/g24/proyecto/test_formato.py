"""Oraculo congelado G24: el formato no cambia lo que la funcion devuelve."""

import unittest

from formato import etiqueta_corta, etiqueta_evento


class EtiquetaEventoTest(unittest.TestCase):

    def test_arma_la_etiqueta(self):
        self.assertEqual(etiqueta_evento('KDD', 'Rosario', 'AR'),
                         'KDD - Rosario, AR')

    def test_recorta_los_espacios(self):
        self.assertEqual(etiqueta_evento('  KDD ', ' Lima', 'PE  '),
                         'KDD - Lima, PE')

    def test_partes_vacias(self):
        self.assertEqual(etiqueta_evento('', '', ''), ' - , ')

    def test_etiqueta_corta(self):
        self.assertEqual(etiqueta_corta('  kdd '), 'KDD')

    def test_etiqueta_corta_vacia(self):
        self.assertEqual(etiqueta_corta('   '), '')
