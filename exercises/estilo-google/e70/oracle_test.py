"""Oraculo congelado: el comando sigue siendo el mismo.
"""

import os
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))


def texto():
    with open(os.path.join(AQUI, 'target.md'), encoding='utf-8') as fh:
        return fh.read()



class SintaxisTest(unittest.TestCase):

    def test_el_comando_sigue_siendo_el_mismo(self):
        self.assertTrue(texto().startswith('gcloud deploy'))
        self.assertIn('region', texto().lower())


if __name__ == '__main__':
    unittest.main()
