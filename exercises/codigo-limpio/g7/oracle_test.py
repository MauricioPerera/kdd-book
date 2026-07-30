"""Oraculo congelado G7.

Refactor puro: mover la eleccion del canal fuera de la clase base no cambia
que canal se elige. El oraculo pasa igual antes y despues.
"""

import unittest

from target import Email, Notificacion


class NotificacionTest(unittest.TestCase):

    def test_canal_de_la_base(self):
        self.assertEqual(Notificacion('ana').canal(), 'ninguno')

    def test_canal_de_la_variante(self):
        self.assertEqual(Email('ana').canal(), 'email')

    def test_la_preferida_es_email(self):
        self.assertEqual(Notificacion('ana').preferida().canal(), 'email')

    def test_la_preferida_conserva_el_destino(self):
        self.assertEqual(Notificacion('ana').preferida().destino, 'ana')

    def test_email_hereda_de_notificacion(self):
        self.assertIsInstance(Email('ana'), Notificacion)


if __name__ == '__main__':
    unittest.main()
