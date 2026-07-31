"""Oraculo congelado: los dos items siguen estando.
"""

import os
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))


def texto():
    with open(os.path.join(AQUI, 'target.md'), encoding='utf-8') as fh:
        return fh.read()



class ListaTest(unittest.TestCase):

    def test_los_dos_items_siguen_estando(self):
        self.assertIn('item', texto().lower())
        self.assertEqual(texto().count('\n- ') + (1 if texto().startswith('- ') else 0), 2)


if __name__ == '__main__':
    unittest.main()
