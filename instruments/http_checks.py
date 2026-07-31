#!/usr/bin/env python3
"""Instrumentos que miden sobre respuestas HTTP (documentacion de htmx).

Las otras familias leen codigo, el proyecto o el historial. Estas dos tecnicas
hablan de lo que el servidor **devuelve**, y el proyecto prohibe red: nada de
salir a pedirle a un host. La salida es la misma que usa `arch_checks` con las
capas — que el proyecto **declare** el artefacto:

    vary  la respuesta que varia segun HX-Request lo dice con `Vary`
    csp   la respuesta trae la politica de seguridad con las directivas exigidas

El instrumento lee **capturas de intercambios**, no hace peticiones. Una
captura es un archivo con el formato de la propia HTTP:

    GET /fragmento
    HX-Request: true

    200
    Content-Type: text/html; charset=utf-8
    Vary: HX-Request

    <div>lo que devolvio</div>

Es decir: linea de peticion, cabeceras de peticion, linea en blanco, codigo de
estado, cabeceras de respuesta, linea en blanco, cuerpo. Producir esas capturas
es responsabilidad del proyecto —un test, un `curl -v`, un proxy— igual que
declarar sus capas.

Solo stdlib.

Exit codes (convencion KDD):
  0  la propiedad se cumple
  1  no se cumple
  2  no se pudo verificar (captura ilegible, o falta lo que hay que comparar)

Uso:
    python http_checks.py --rule vary <capturas/>
    python http_checks.py --rule csp --exige default-src --exige connect-src <capturas/>
    python http_checks.py --list
"""

import argparse
import email.parser
import glob
import hashlib
import os
import re
import sys


class NoVerificable(Exception):
    """Falta el dato sin el cual la regla no se puede evaluar (exit 2)."""


class Intercambio:
    __slots__ = ('archivo', 'metodo', 'ruta', 'peticion', 'estado', 'respuesta', 'cuerpo')

    def __init__(self, archivo, metodo, ruta, peticion, estado, respuesta, cuerpo):
        self.archivo = archivo
        self.metodo = metodo
        self.ruta = ruta
        self.peticion = peticion
        self.estado = estado
        self.respuesta = respuesta
        self.cuerpo = cuerpo

    @property
    def clave(self):
        return (self.metodo, self.ruta)

    def cabecera_peticion(self, nombre):
        return self.peticion.get(nombre)

    def cabecera_respuesta(self, nombre):
        return self.respuesta.get(nombre)

    def huella(self):
        return hashlib.sha256(self.cuerpo.encode('utf-8')).hexdigest()[:12]


def _cabeceras(texto):
    return email.parser.Parser().parsestr(texto)


def parsear(ruta):
    """Lee una captura. Lanza NoVerificable si no tiene la forma declarada."""
    with open(ruta, 'r', encoding='utf-8') as fh:
        crudo = fh.read().replace('\r\n', '\n')
    partes = crudo.split('\n\n')
    if len(partes) < 2:
        raise NoVerificable(
            '{}: no tiene la forma de una captura (peticion, linea en blanco, '
            'respuesta)'.format(os.path.basename(ruta)))

    bloque_peticion = partes[0].splitlines()
    if not bloque_peticion:
        raise NoVerificable('{}: captura vacia'.format(os.path.basename(ruta)))
    linea = bloque_peticion[0].split()
    if len(linea) < 2:
        raise NoVerificable(
            '{}: la primera linea deberia ser "METODO /ruta", se leyo {!r}'
            .format(os.path.basename(ruta), bloque_peticion[0]))
    metodo, ruta_pedida = linea[0], linea[1]
    peticion = _cabeceras('\n'.join(bloque_peticion[1:]))

    bloque_respuesta = partes[1].splitlines()
    if not bloque_respuesta or not bloque_respuesta[0].strip().split()[0].isdigit():
        raise NoVerificable(
            '{}: la respuesta deberia empezar por el codigo de estado'
            .format(os.path.basename(ruta)))
    estado = int(bloque_respuesta[0].strip().split()[0])
    respuesta = _cabeceras('\n'.join(bloque_respuesta[1:]))
    cuerpo = '\n\n'.join(partes[2:])
    return Intercambio(ruta, metodo, ruta_pedida, peticion, estado, respuesta, cuerpo)


def capturas(rutas):
    archivos = []
    for r in rutas:
        if os.path.isdir(r):
            archivos.extend(sorted(glob.glob(os.path.join(r, '*.http'))))
        else:
            archivos.append(r)
    if not archivos:
        raise NoVerificable('no se encontraron capturas (*.http)')
    return [parsear(a) for a in archivos]


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_vary(intercambios, opts):
    """La respuesta que varia segun HX-Request tiene que declararlo.

    La documentacion lo dice sin ambiguedad: si el servidor devuelve el HTML
    completo cuando falta `HX-Request` y un fragmento cuando vale `true`, hace
    falta `Vary: HX-Request`, porque si no la cache sirve el fragmento a quien
    pidio la pagina entera.

    No se adivina si varia: **se demuestra**. Hacen falta dos capturas de la
    misma ruta, una con la cabecera y otra sin ella, y cuerpos distintos. Con
    una sola captura no hay nada que comparar, y decirlo es mas honesto que dar
    verde.
    """
    por_ruta = {}
    for i in intercambios:
        por_ruta.setdefault(i.clave, []).append(i)

    comparables = 0
    out = []
    for (metodo, ruta), grupo in sorted(por_ruta.items()):
        con = [i for i in grupo if (i.cabecera_peticion('HX-Request') or '').lower() == 'true']
        sin = [i for i in grupo if (i.cabecera_peticion('HX-Request') or '').lower() != 'true']
        if not con or not sin:
            continue
        comparables += 1
        if con[0].huella() == sin[0].huella():
            continue  # no varia: no hace falta declararlo
        declarado = con[0].cabecera_respuesta('Vary') or ''
        if 'hx-request' not in declarado.lower():
            out.append(('{} {}: la respuesta cambia segun HX-Request ({} contra {}) '
                        'y no declara `Vary: HX-Request`{}'
                        .format(metodo, ruta, con[0].huella(), sin[0].huella(),
                                ' (declara {!r})'.format(declarado) if declarado else ''),
                        False))
    if not comparables:
        raise NoVerificable(
            'ninguna ruta tiene dos capturas comparables (una con HX-Request y '
            'otra sin el): no hay con que demostrar si la respuesta varia')
    return out


_META_CSP = re.compile(
    r'<meta[^>]+http-equiv=["\']Content-Security-Policy["\'][^>]*content=["\']([^"\']*)',
    re.I)


def check_csp(intercambios, opts):
    """La respuesta trae la politica de seguridad con las directivas exigidas.

    Las directivas se declaran con `--exige`, y eso no es burocracia: "tener una
    CSP" no es verificable si no se dice que tiene que contener. Una politica
    vacia es una CSP igual, y daria verde.

    Vale tanto la cabecera como el `<meta http-equiv>` del cuerpo, que es la
    forma que muestra la documentacion de htmx.
    """
    if not opts.exige:
        raise NoVerificable(
            'hay que declarar las directivas con --exige (por ejemplo '
            '--exige default-src): "tener una CSP" sin decir cual no es verificable')
    exigidas = [d.strip() for e in opts.exige for d in e.split(',') if d.strip()]

    out = []
    for i in intercambios:
        if not (i.respuesta.get('Content-Type') or '').lower().startswith('text/html'):
            continue
        politica = i.cabecera_respuesta('Content-Security-Policy') or ''
        if not politica:
            m = _META_CSP.search(i.cuerpo)
            politica = m.group(1) if m else ''
        if not politica:
            out.append(('{} {}: respuesta HTML sin Content-Security-Policy, ni en '
                        'cabecera ni en <meta>'.format(i.metodo, i.ruta), False))
            continue
        faltan = [d for d in exigidas if d not in politica]
        if faltan:
            out.append(('{} {}: la politica no declara {}'
                        .format(i.metodo, i.ruta, ', '.join(faltan)), False))
    return out


RULES = {
    'csp': (check_csp, 'CSP: la respuesta trae la politica con las directivas exigidas'),
    'vary': (check_vary, 'Vary: la respuesta que varia segun HX-Request lo declara'),
}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--rule')
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--exige', action='append',
                        help='directiva que la CSP debe declarar; repetible')
    # Las capturas se declaran aparte del positional a proposito: en un
    # contrato lo que se EDITA es la app y lo que se MIDE son las respuestas
    # que produce. Confundirlos haria que el ejercicio midiera el archivo que
    # se esta tocando.
    parser.add_argument('--capturas')
    parser.add_argument('files', nargs='*')
    args = parser.parse_args(argv)

    if args.list:
        for nombre in sorted(RULES):
            print('{:6} {}'.format(nombre, RULES[nombre][1]))
        return 0

    if args.rule not in RULES:
        print('NO-VERIFICABLE: regla desconocida: {!r} (ver --list)'.format(args.rule))
        return 2
    fuentes = [args.capturas] if args.capturas else args.files
    if not fuentes:
        print('NO-VERIFICABLE: no se indicaron capturas')
        return 2

    func, etiqueta = RULES[args.rule]
    try:
        hallazgos = func(capturas(fuentes), args)
    except NoVerificable as exc:
        print('NO-VERIFICABLE: {}: {}'.format(etiqueta, exc))
        return 2
    except OSError as exc:
        print('NO-VERIFICABLE: {}: {}'.format(etiqueta, exc))
        return 2

    if hallazgos:
        print('INSTRUMENTO ROJO: {}'.format(etiqueta))
        for mensaje, _ in hallazgos:
            print('  {}'.format(mensaje))
        return 1

    print('OK: {}'.format(etiqueta))
    return 0


if __name__ == '__main__':
    sys.exit(main())
