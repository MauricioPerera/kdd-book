"""Oraculo congelado: el giro falla y funciona igual, con el nombre de destino.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import target  # noqa: E402


class ComportamientoTest(unittest.TestCase):

    def test_lo_observable_no_cambia(self):
        self.assertEqual(target.girar(100, 30), 70)
        with self.assertRaises(target.SaldoInsuficienteError):
            target.girar(10, 30)


if __name__ == '__main__':
    unittest.main()
