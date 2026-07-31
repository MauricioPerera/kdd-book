"""Oraculo congelado: los datos de la tabla no cambian.
"""

import os
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))


def texto():
    with open(os.path.join(AQUI, 'target.md'), encoding='utf-8') as fh:
        return fh.read()



class TablaTest(unittest.TestCase):

    def test_los_datos_no_cambian(self):
        self.assertIn('| 1 | 2 |', texto())
        self.assertIn('| a | b |', texto())


if __name__ == '__main__':
    unittest.main()
