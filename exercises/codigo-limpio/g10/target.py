"""Solucion G10: la variable se declara donde se usa."""


def resumen_evento(nombre, capacidad, inscriptos, activo):
    if not activo:
        return 'inactivo'
    if capacidad <= 0:
        return 'sin capacidad'
    if inscriptos > capacidad:
        return 'sobrevendido'
    if inscriptos == capacidad:
        return 'completo'
    etiqueta = nombre.strip().upper()
    return etiqueta
