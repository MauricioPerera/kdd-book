"""Oraculo congelado: la imagen sigue siendo el mismo archivo.
"""

import os
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))


def texto():
    with open(os.path.join(AQUI, 'target.md'), encoding='utf-8') as fh:
        return fh.read()



class ImagenTest(unittest.TestCase):

    def test_la_imagen_sigue_siendo_la_misma(self):
        self.assertIn('diagram.png', texto())


if __name__ == '__main__':
    unittest.main()
