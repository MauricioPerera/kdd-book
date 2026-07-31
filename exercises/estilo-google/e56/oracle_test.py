"""Oraculo congelado: el aviso dice lo mismo.
"""

import os
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))


def texto():
    with open(os.path.join(AQUI, 'target.md'), encoding='utf-8') as fh:
        return fh.read()



class AvisoTest(unittest.TestCase):

    def test_el_aviso_dice_lo_mismo(self):
        self.assertIn('take a while', texto())


if __name__ == '__main__':
    unittest.main()
