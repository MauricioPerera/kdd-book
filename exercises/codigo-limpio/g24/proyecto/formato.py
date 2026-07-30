"""Etiquetas del proyecto, con el formato en orden."""


def etiqueta_evento(nombre, ciudad, pais):
    partes = (nombre.strip(), ciudad.strip(), pais.strip())
    return '{} - {}, {}'.format(*partes)


def etiqueta_corta(nombre):
    return nombre.strip().upper()
