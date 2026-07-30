"""Punto de partida: el servicio se fabrica su propia dependencia."""

from tarifas_dao import TarifaDAO


class ServicioTarifas:
    def __init__(self):
        self.dao = TarifaDAO()

    def con_recargo(self, porcentaje):
        return self.dao.base() * (100 + porcentaje) // 100
