"""Oraculo congelado del ejercicio de instanciacion.

Escrito contra la firma de destino: quitar la creacion de la dependencia
cambia el constructor, asi que el seed arranca en rojo. El instrumento sigue
haciendo falta, porque nada impide recibir el DAO y ademas crearse otro.
"""

import unittest

from servicio import ServicioTarifas
from tarifas_dao import TarifaDAO


class DAOFalso:
    def base(self):
        return 200


class ServicioTarifasTest(unittest.TestCase):

    def test_recargo_con_el_dao_real(self):
        self.assertEqual(ServicioTarifas(TarifaDAO()).con_recargo(10), 110)

    def test_sin_recargo(self):
        self.assertEqual(ServicioTarifas(TarifaDAO()).con_recargo(0), 100)

    def test_acepta_otro_dao(self):
        self.assertEqual(ServicioTarifas(DAOFalso()).con_recargo(0), 200)

    def test_el_dao_falso_cambia_el_resultado(self):
        self.assertEqual(ServicioTarifas(DAOFalso()).con_recargo(50), 300)

    def test_guarda_el_dao_que_recibe(self):
        dao = DAOFalso()
        self.assertIs(ServicioTarifas(dao).dao, dao)
