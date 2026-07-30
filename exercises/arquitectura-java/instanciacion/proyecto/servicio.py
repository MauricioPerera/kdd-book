"""Solucion: la dependencia se la asigna un agente externo."""


class ServicioTarifas:
    def __init__(self, dao):
        self.dao = dao

    def con_recargo(self, porcentaje):
        return self.dao.base() * (100 + porcentaje) // 100
