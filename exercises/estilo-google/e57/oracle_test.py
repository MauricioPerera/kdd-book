"""Oraculo congelado: la espera no cambia.
"""

import os
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))


def texto():
    with open(os.path.join(AQUI, 'target.md'), encoding='utf-8') as fh:
        return fh.read()



class EsperaTest(unittest.TestCase):

    def test_la_espera_no_cambia(self):
        self.assertIn('seconds before retrying', texto().lower())


if __name__ == '__main__':
    unittest.main()
