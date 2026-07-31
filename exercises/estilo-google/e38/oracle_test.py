"""Oraculo congelado: los tres elementos siguen estando.
"""

import os
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))


def texto():
    with open(os.path.join(AQUI, 'target.md'), encoding='utf-8') as fh:
        return fh.read()



class EnumeracionTest(unittest.TestCase):

    def test_los_tres_elementos_siguen_estando(self):
        for elemento in ('apples', 'bananas', 'cherries'):
            self.assertIn(elemento, texto())


if __name__ == '__main__':
    unittest.main()
