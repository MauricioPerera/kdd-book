"""Oraculo congelado: el pedido acumula igual, con los nombres de destino.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import target  # noqa: E402


class ComportamientoTest(unittest.TestCase):

    def test_lo_observable_no_cambia(self):
        p = target.Pedido()
        self.assertEqual(p.agregar_item(10), 1)
        self.assertEqual(p.items, [10])


if __name__ == '__main__':
    unittest.main()
