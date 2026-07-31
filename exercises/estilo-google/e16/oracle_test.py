"""Oraculo congelado: sigue hablando de la misma operacion.
"""

import os
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))


def texto():
    with open(os.path.join(AQUI, 'target.md'), encoding='utf-8') as fh:
        return fh.read()



class FraseTest(unittest.TestCase):

    def test_sigue_hablando_de_la_operacion(self):
        self.assertIn('operation', texto())


if __name__ == '__main__':
    unittest.main()
