"""Punto de partida G10: la variable se declara lejos de donde se usa."""


def resumen_evento(nombre, capacidad, inscriptos, activo):
    etiqueta = nombre.strip().upper()
    if not activo:
        return 'inactivo'
    if capacidad <= 0:
        return 'sin capacidad'
    if inscriptos > capacidad:
        return 'sobrevendido'
    if inscriptos == capacidad:
        return 'completo'
    return etiqueta
