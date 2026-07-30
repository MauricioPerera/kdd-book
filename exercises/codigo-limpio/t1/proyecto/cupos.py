"""Estado de un evento segun sus cupos."""


def estado(capacidad, inscriptos, activo):
    """Etiqueta el estado del evento."""
    if not activo:
        return 'inactivo'
    if capacidad <= 0:
        return 'sin capacidad'
    if inscriptos > capacidad:
        return 'sobrevendido'
    if inscriptos == capacidad:
        return 'completo'
    return 'disponible'
