"""Oraculo congelado: el enlace interno sigue escrito igual.
"""

import os
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))


def texto():
    with open(os.path.join(AQUI, 'target.md'), encoding='utf-8') as fh:
        return fh.read()



class EnlaceTest(unittest.TestCase):

    def test_el_enlace_sigue_apuntando_al_mismo_lado(self):
        self.assertIn('[Options](#options)', texto())


if __name__ == '__main__':
    unittest.main()
