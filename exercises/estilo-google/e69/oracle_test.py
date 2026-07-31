"""Oraculo congelado: los tres argumentos siguen estando.
"""

import os
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))


def texto():
    with open(os.path.join(AQUI, 'target.md'), encoding='utf-8') as fh:
        return fh.read()



class LlamadaTest(unittest.TestCase):

    def test_los_tres_argumentos_siguen_estando(self):
        for arg in ('argument_one', 'argument_two', 'argument_three'):
            self.assertIn(arg, texto())


if __name__ == '__main__':
    unittest.main()
