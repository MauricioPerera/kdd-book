"""El motor de plantillas del proyecto. Fixture: no se toca.

Es un mustache minimo —secciones, valor escapado, y las dos salidas de escape—
y esta aca por una razon de forma. El comportamiento observable de una
plantilla es **lo que renderiza**, y sin un motor el oraculo no tendria nada
que fijar. Los ejercicios de HTTP resolvieron lo mismo con una app que produce
respuestas; aca el proyecto declara con que renderiza, igual que declara sus
capas para `arch_checks`.

Que sea independiente de `template_checks` es a proposito, y es la misma regla
que siguen los oraculos de HTML: el instrumento dice si la tecnica se aplico y
el motor dice que se ve. Si compartieran codigo, un error de escapado los haria
coincidir a los dos y nadie lo notaria.
"""

import html
import re

# `{{#lista}}...{{/lista}}`: la retrovisita \1 exige que cierre la misma seccion.
SECCION = re.compile(r'\{\{#\s*(\w+)\s*\}\}(.*?)\{\{/\s*\1\s*\}\}', re.S)

# Las dos salidas de escape de mustache. Insertan tal cual lo que reciben.
CRUDO = re.compile(r'\{\{\{\s*(\w+)\s*\}\}\}|\{\{&\s*(\w+)\s*\}\}')

# El valor normal, que escapa. Va DESPUES de CRUDO: `{{{x}}}` contiene un
# `{{x}}` y al reves se escaparia lo que la plantilla pidio crudo.
VALOR = re.compile(r'\{\{\s*(\w+)\s*\}\}')


def render(plantilla, datos):
    def _seccion(m):
        cuerpo = m.group(2)
        partes = []
        for item in datos.get(m.group(1)) or []:
            contexto = dict(datos)
            contexto.update(item)
            partes.append(render(cuerpo, contexto))
        return ''.join(partes)

    def _crudo(m):
        return str(datos.get(m.group(1) or m.group(2), ''))

    def _valor(m):
        return html.escape(str(datos.get(m.group(1), '')), quote=True)

    salida = SECCION.sub(_seccion, plantilla)
    salida = CRUDO.sub(_crudo, salida)
    return VALOR.sub(_valor, salida)
