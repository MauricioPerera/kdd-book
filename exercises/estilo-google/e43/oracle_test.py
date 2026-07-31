"""Oraculo congelado: los dos pasos siguen estando.
"""

import os
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))


def texto():
    with open(os.path.join(AQUI, 'target.md'), encoding='utf-8') as fh:
        return fh.read()



class PasosTest(unittest.TestCase):

    def test_los_dos_pasos_siguen_estando(self):
        self.assertIn('First step', texto())
        self.assertIn('Second step', texto())


if __name__ == '__main__':
    unittest.main()
