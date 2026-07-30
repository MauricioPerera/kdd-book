"""Etiquetas del proyecto, con el formato descuidado."""


def etiqueta_evento(nombre, ciudad, pais):   
	return nombre.strip() + " - " + ciudad.strip() + ", " + pais.strip()  # una linea larguisima que se estira mucho mas alla de lo razonable y obliga a scrollear


def etiqueta_corta(nombre):	
    return nombre.strip().upper()