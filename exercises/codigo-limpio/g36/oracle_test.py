"""Oraculo congelado del ejercicio G36.

Fija el comportamiento observable de `etiqueta_envio` y los constructores que
forman su interfaz. No sabe nada de la Ley de Demeter, y esa independencia es
deliberada: una refactorizacion no cambia el comportamiento, asi que este
archivo pasa igual antes y despues. Quien discrimina si la tecnica quedo
aplicada es el instrumento, no el oraculo.
"""

import unittest

from target import Cliente, Direccion, Pedido, etiqueta_envio


def _pedido(ciudad='Rosario', pais='AR', codigo='S2000'):
    return Pedido('A-1', Cliente('Ana', Direccion(ciudad, pais, codigo)))


class EtiquetaEnvioTest(unittest.TestCase):

    def test_formato_completo(self):
        self.assertEqual(etiqueta_envio(_pedido()), 'Rosario, AR (S2000)')

    def test_usa_los_tres_campos_de_la_direccion(self):
        etiqueta = etiqueta_envio(_pedido('Lisboa', 'PT', '1100-048'))
        self.assertEqual(etiqueta, 'Lisboa, PT (1100-048)')

    def test_no_depende_del_numero_de_pedido(self):
        uno = Pedido('A-1', Cliente('Ana', Direccion('Lima', 'PE', '15001')))
        otro = Pedido('Z-999', Cliente('Ana', Direccion('Lima', 'PE', '15001')))
        self.assertEqual(etiqueta_envio(uno), etiqueta_envio(otro))

    def test_no_depende_del_nombre_del_cliente(self):
        ana = Pedido('A-1', Cliente('Ana', Direccion('Lima', 'PE', '15001')))
        beto = Pedido('A-1', Cliente('Beto', Direccion('Lima', 'PE', '15001')))
        self.assertEqual(etiqueta_envio(ana), etiqueta_envio(beto))

    def test_campos_vacios_se_propagan_tal_cual(self):
        self.assertEqual(etiqueta_envio(_pedido('', '', '')), ',  ()')

    def test_no_recorta_ni_normaliza(self):
        self.assertEqual(etiqueta_envio(_pedido(' Quito ', 'ec', '  ')),
                         ' Quito , ec (  )')


if __name__ == '__main__':
    unittest.main()
