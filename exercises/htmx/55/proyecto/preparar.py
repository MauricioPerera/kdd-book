"""Deriva las capturas de la app. No las escribe a mano.

Este paso existe porque lo que se edita y lo que se mide no son el mismo
archivo: se toca la app y se miden las respuestas que produce. Si las capturas
fueran el target, el ejercicio enseniaria a falsificar la evidencia en vez de
arreglar la causa.
"""

import os
import shutil

from app import responder

AQUI = os.path.dirname(os.path.abspath(__file__))
DESTINO = os.path.join(AQUI, 'capturas')

PETICIONES = [('completo.http', {}), ('fragmento.http', {'HX-Request': 'true'})]


def main():
    shutil.rmtree(DESTINO, ignore_errors=True)
    os.makedirs(DESTINO)
    for archivo, cabeceras in PETICIONES:
        estado, salida, cuerpo = responder('/inscriptos', cabeceras)
        lineas = ['GET /inscriptos']
        lineas += ['{}: {}'.format(k, v) for k, v in cabeceras.items()]
        lineas += ['', str(estado)]
        lineas += ['{}: {}'.format(k, v) for k, v in salida.items()]
        lineas += ['', cuerpo]
        with open(os.path.join(DESTINO, archivo), 'w', encoding='utf-8',
                  newline='\n') as fh:
            fh.write('\n'.join(lineas) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
