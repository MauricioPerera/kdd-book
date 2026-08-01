#!/usr/bin/env python3
"""Emisor determinista del libro de conocimiento Effective Go.

Fase 1 del pipeline: escribe `books/effective-go.json`, un grafo OKF-node lista
para okf_emit.py, a partir de las tecnicas extrauidas de la pagina
go.dev/doc/effective_go.

El triaje esta codificado, no inferido:

  - pila A (contractable, instrumented): indentation-tabs (eg01),
    no-paren-control (eg02), brace-next-line (eg03). Tres convenciones de
    formato cuyo artefacto (un archivo .go) admite una comprobacion
    determinista basada en regex de texto.
  - pila B (no-especificable): doc-comment-before-declaration (eg04),
    comma-ok-assertion (eg05), defer-close-paired (eg06),
    error-string-lowercase (eg07), error-return-checked (eg08),
    receiver-name-convention (eg09). Tecnicas con una propiedad de texto
    proxy, pero un algoritmo de verificacion preciso requiere parseo simbolico
    o analisis de flujo de datos.
  - pila C (conocimiento): 36 nodos (eg10..eg45) cubriendo Formatting,
    Commentary, Names, Semicolons, Control structures, Data, Methods,
    Interfaces, The blank identifier, Embedding, Concurrency, Errors,
    Panic, Recover. Politicas y convenciones del toolchain (gofmt + lint)
    que no hay invariante de texto localizable; son conocimiento que el
    estilo de ida y la revision humana operacionalizan.

WHY_NOT documenta por que cada B no es contractable.

Exit codes (convencion KDD):
  0  libro emitido
  1  error de contenido
  2  no se pudo verificar (entrada ilegible, salida no escribible)

Uso:
    python build_effective_go.py [--out books/effective-go.json]
"""

__all__ = ['build', 'main']

import argparse
import json
import os
import sys


# --- Triaje estatico ---------------------------------------------------------

# Pila A -> regla del instrumento effective_go_checks.py que la mide.
A_NODES = {
    1: 'indentation-tabs',
    2: 'no-paren-control',
    3: 'brace-next-line',
}

# Pila B -> tecnicas con why_not.
B_NODES = {4, 5, 6, 7, 8, 9}

# Pila C -> tecnicas de conocimiento.
C_INDICES = set(range(10, 46))  # eg10..eg45


# Por que cada B no es contractable.
WHY_NOT = {
    4: ("Verificar que un comentario de doc preceda a la declaracion y que "
        "el comentario comience con el nombre exacto del identificador "
        "exportado requiere asociar el texto del comentario al simbolo "
        "declarado. Un proxy de texto (presencia de `//` antes de `func`) "
        "no comprueba que el comentario mencione el nombre correcto: "
        "`func Foo()` documentado con `// Bar does stuff` pasaria el proxy "
        "pero falla la regla real. Requiere parseo de nombres simbolicos, "
        "no solo regex sobre lineas aisladas."),
    5: ("La tecnica es el uso del patron comma-ok en aserciones de tipo "
        "(`v, ok := x.(T)`). Pero el codigo correcto tambien usa `x.(T)` "
        "(conversion directa, una sola vez) o en type-switch "
        "(`switch v := x.(type)`). Un instrumento de texto sobre "
        "`x.(T)` no distingue conversion segura con comma-ok de "
        "conversion directa intencional sin analizar el flujo de control "
        "y las intenciones del programador: es una decision de diseno, "
        "no una propiedad localizable en una linea aislada."),
    6: ("Verificar que `os.Open` tiene un `defer ...Close()` correspondiente "
        "requiere rastrear el nombre de la variable devuelta hasta su uso en "
        "defer, saltando lineas intermedias y manejando shadowing. Un proxy "
        "regex `os.Open.*defer.*Close` es frágil: un Open sin Close "
        "intencional (paso de file descriptor a otra funcion) produce un "
        "falso positivo, y un defer sin el nombre exacto de la variable "
        "produce un falso negativo. Requiere analisis de flujo de datos, "
        "no solo regex sobre texto aislado."),
    7: ("Detectar si un error esta capitalizado implica identificar que un "
        "string literal es un error (no un mensaje arbitrario de log), "
        "rastrear el contexto `errors.New` o `fmt.Errorf`, y luego "
        "inspeccionar la capitalizacion. El mismo string literal podria "
        "ser un mensaje de log, un nombre de archivo o un error segun el "
        "contexto. Un proxy de texto sobre `errors.New(\"...\"`) con "
        "mayuscula inicial no distingue errores de otros strings, y no "
        "verifica el encadenamiento con `fmt.Errorf` que también debe "
        "empezar en minuscula. Requiere analisis semantico, no solo regex."),
    8: ("Verificar que un valor de error devuelto es comprobado requiere "
        "conocer la firma de la funcion llamada (¿devuelve error?), rastrear "
        "el nombre de la variable asignada y comprobar que se usa en una "
        "condicion `if err != nil` o se propaga con `return err`. Un proxy "
        "de texto sobre `_ = foo()` captura el caso mas evidente, pero no "
        "detecta `foo()` cuyo error se ignora implicitamente (la llamada "
        "sin asignacion), ni distingue un `_` intencional (funcion que no "
        "devuelve error) de uno accidental. Requiere analisis de tipos y "
        "flujo de datos, no solo regex sobre texto aislado."),
    9: ("Verificar consistencia de nombres de receiver requiere agrupar "
        "todos los metodos que operan sobre el mismo tipo, asociando cada "
        "declaracion `func (nombre Tipo) Metodo()` al tipo Tipo. Un proxy "
        "de texto sobre una sola linea no puede determinar que dos metodos "
        "pertenecen al mismo tipo sin parsear el identificador del tipo "
        "entre parentesis. Requiere analisis de simbolos globales, no solo "
        "regex sobre lineas aisladas."),
}

# Alias. Obligatorio y no vacio para A y B; vacio para C (como en stripe.json).
ALIAS = {
    1: ['tabs', 'tabulaciones', 'gofmt', 'sangria'],
    2: ['sin parentesis', 'control structures', 'no parentheses'],
    3: ['llave en misma linea', 'brace on same line', 'gofmt'],
    4: ['doc comment', 'documentacion', 'go doc'],
    5: ['comma-ok', 'type assertion', 'type-safe'],
    6: ['defer close', 'resource leak', 'defer'],
    7: ['error string', 'lowercase', 'capitalization'],
    8: ['error handling', 'comprobar error', 'error return'],
    9: ['receiver name', 'nombre de receiver', 'consistencia'],
}

# Titulos cortos (una etiqueta por nodo). Ninguna palabra >3 chars es subcadena
# del id: los ids son eg01..eg45, de los que ninguna palabra de titulo coincide.
TITULOS = {
    1: 'Indentacion: tabs no espacios',
    2: 'Sin parentesis en estructuras de control',
    3: 'Llave de apertura en la misma linea',
    4: 'Doc comment antes de la declaracion',
    5: 'Comma-ok en aserciones de tipo',
    6: 'Deferir Close tras abrir un recurso',
    7: 'Error strings en minuscula',
    8: 'Verificar valores de error devueltos',
    9: 'Receiver con nombre consistente por tipo',
    10: 'Nombres de paquete: minusculas sin guion bajo',
    11: 'Getters sin prefijo get',
    12: 'Interfaces con sufijo -er',
    13: 'Identificadores MixedCaps (camelCase)',
    14: 'Sin limite de longitud de linea',
    15: 'gofmt: formateo automatico con tabs',
    16: 'Insercion automatica de semicolons',
    17: 'Comentarios: linea y bloque',
    18: 'Tres formas de for',
    19: 'Switch sin fallthrough automatico',
    20: 'Range sobre arrays, slices, maps, canales',
    21: 'Multiples valores de retorno',
    22: 'Resultados nombrados en return',
    23: 'defer: ejecutar antes del return',
    24: 'new: memoria zeroada; make: inicializa slices/maps/channels',
    25: 'Literales compuestos: field: value',
    26: 'Arrays son valores, no referencias',
    27: 'len y cap: longitud vs capacidad',
    28: 'Slices bidimensionales: slice-of-slices',
    29: 'Comma-ok para map keys: missing vs zero value',
    30: 'delete() es seguro incluso si la key no existe',
    31: 'Familia fmt: Print, Printf, Fprint, Sprint',
    32: 'append devuelve el slice actualizado',
    33: 'init(): inicializacion antes de main',
    34: 'Receiver por puntero para mutacion, por valor para lectura',
    35: 'Interfaces: tipado estructural sin declaracion explicita',
    36: 'Conversiones entre tipos',
    37: 'Type switch: switch v := x.(type)',
    38: 'Identificador en blanco: descartar valores',
    39: '_ para silenciar imports y variables no usados',
    40: 'Import para efectos secundarios: import _',
    41: 'Checks de interfaz en tiempo de compilacion',
    42: 'Embedding: tipos dentro de struct e interface',
    43: 'Compartir por comunicacion (no por memoria)',
    44: 'Goroutines: concurrencia ligera',
    45: 'recover(): detener panic en deferred',
}

# Umbral humano por regla A: "cero violaciones" (el instrumento devuelve []).
THRESHOLD = {
    'indentation-tabs': ('cero lineas de .go con sangria en espacios '
                         '(gofmt usa tabulaciones exclusivamente)'),
    'no-paren-control': ('cero parentesis alrededor de la condicion de '
                         'if/for/switch (Go no usa parentesis en estructuras '
                         'de control)'),
    'brace-next-line': ('cero llaves de apertura en linea separada de '
                        'if/for/switch/func (el `{` va en la misma linea '
                        'que la keyword)'),
}

# Descripciones detalladas por indice. Extrauidas de la narrativa de
# Effective Go (go.dev/doc/effective_go), reescritas como invariantes
# contractables o de conocimiento.
DESCRIPCIONES = {
    1: ("gofmt usa tabulaciones para la sangria. Un archivo .go cuyas lineas "
        "interiorizadas empiecen con espacios en vez de un tabulador no "
        "cumple la convencion de formato que el toolchain gofmt aplica y "
        "revierte automaticamente; la sangria debe ser siempre un tab."),
    2: ("Las estructuras de control de Go (if, for, switch) no llevan "
        "parentesis alrededor de la condicion. Escribir `if (x > 0)` o "
        "`for (i := 0; i < n; i++)` es valido sintacticamente pero no "
        "idiomatico: los parentesis son redundantes y la comunidad los "
        "rechaza. El cuerpo del if sigue en la misma linea que la condicion."),
    3: ("La llave de apertura de un bloque va en la misma linea que la "
        "keyword (if, for, switch, func). Ponerla en la linea siguiente, "
        "el estilo de C/Java, rompe el formato que gofmt impone como regla "
        "unica: `if cond {\\n    ...\\n}` no `if cond\\n{`."),
    4: ("Todo identificador exportable (funciones, tipos, metodos, "
        "variables) debe tener un comentario de doc que empiece con su "
        "nombre. El comentario no es solo estilo: `go doc` lo muestra y "
        "`go vet` lo advierte. Un identificador exportado sin doc es un "
        "defecto de API."),
    5: ("Cuando se convierte un valor a un tipo de interfaz conocido, usar "
        "el patron comma-ok (`v, ok := x.(T)`) para distinguir si la "
        "conversion es segura. Una conversion directa `x.(T)` que falla "
        "hace panic; el patron comma-ok evita el panic con una bandera "
        "booleana que indica si la conversion tuvo exito."),
    6: ("Cuando se abre un recurso (os.Open, os.Create, http.Get), el Close "
        "debe deferirse inmediatamente para garantizar que se libere incluso "
        "si ocurre un error intermedio. Es el patron 'abrir- deferir-cierre' "
        "del que Effective Go advierte: sin defer, un return intermedio puede "
        "saltar el Close y producir un leak de descriptor de archivo."),
    7: ("Los strings de error no deben empezar con Mayuscula ni contener "
        "saltos de linea. La convencion de Go es que los errores son frases "
        "en minuscula inicial: 'file not found', no 'File not found'. Esto "
        "evita mayusculas dobles cuando el error se encadena en un mensaje "
        "mayor y evita confusion en la lectura del log."),
    8: ("En Go, las funciones devuelven un error como ultimo valor de "
        "retorno. El llamador debe comprobar `if err != nil` antes de usar "
        "el resto de los valores. Ignorar el error —por ejemplo con "
        "`_, err := foo()` sin comprobar, o simplemente `foo()`—puede "
        "ocultar fallos que se propagan silenciosamente. Effective Go insiste: "
        "'el error es un valor mas' y siempre se comprueba."),
    9: ("Los metodos de un tipo deben usar el mismo nombre de receiver. "
        "Si el tipo Account tiene metodos con receiver `r`, `a` y `self`, "
        "el codigo es inconsistente y confuso. Effective Go recomienda un "
        "nombre conciso y constante para todos los metodos de un tipo, "
        "evitando abreviaturas ambiguas."),
    10: ("Los paquetes de Go usan solo letras minusculas, sin guiones ni "
        "guiones bajos. Un paquete 'user_auth' deberia ser 'userauth' o, "
        "mejor, dividido en paquetes 'auth' y 'user'. El nombre del paquete "
        "aparece en cada llamada calificada `pkg.Simbolo` y los guiones "
        "bajos lo ensucian visualmente."),
    11: ("Un metodo que devuelve un valor no usa el prefijo 'get': "
        "'obj.Count()' en vez de 'obj.GetCount()'. El prefijo es redundante "
        "en Go. Para getters por referencia el prefijo puede usarse si evita "
        "conflitos, pero no es la convencion comun."),
    12: ("Por convencion, los tipos de interfaz se nombra con el sufijo "
        "del verbo que describe su metodo: 'Reader' para 'Read', 'Writer' "
        "para 'Write'. El patron se usa para interfaces de un solo metodo "
        "que forman parte del API de un paquete."),
    13: ("Go usa MixedCaps (camelCase) para identificadores multi-palabra: "
        "'localName' para locales, 'PublicName' para exportables. Los "
        "guiones bajos en nombres son no idiomaticos; MixedCaps es la "
        "convencion visual que el toolchain aplica consistentemente."),
    14: ("Go no impone un limite de longitud de linea. gofmt no envuelve "
        "lineas. Las lineas largas son aceptables; el lector y su editor "
        "manejan el desplazamiento horizontal. No hay ninguna regla de "
        "longitud maxima de linea en Effective Go ni en gofmt."),
    15: ("gofmt formatea el codigo con tabulaciones para la sangria y "
        "espacios para la alineacion. Los desarrolladores deben correr gofmt "
        "(o `go fmt`) sobre su codigo: el formato es canonical, no es "
        "discutible, y todos los archivos de un proyecto deben seguirlo."),
    16: ("El lexer de Go inserta automaticamente semicolons al final de "
        "lineas que terminan en identificadores, literales, o en ')', ']' o "
        "'}'. Esto significa que la llave de apertura de un bloque debe ir "
        "en la misma linea que la keyword: un '{' en linea separada "
        "recibe un semicolon antes y genera un error de sintaxis."),
    17: ("Los comentarios de linea usan //; los de bloque usan /* */. "
        "Effective Go usa comentarios de bloque para textos grandes del "
        "paquete y comentarios de linea para anotaciones cortas. El paquete "
        "completo va documentado con /* Block */ al inicio del primer archivo."),
    18: ("El bucle `for` es el unico bucle de Go y tiene tres formas: con "
        "clausula init/cond/post (como C), `for cond` (como while) y "
        "`for` sin condicion (infinito). Ademas `range var := range x` "
        "itera sobre arrays, slices, strings, maps y canales."),
    19: ("A diferencia de C/Java, el switch de Go no hace fallthrough "
        "automatico. Cada caso termina implicitamente con break. Se usa "
        "`fallthrough` de forma explicita solo cuando se necesita continuar "
        "al siguiente caso sin cumplir otra condicion."),
    20: ("`range` itera sobre arrays, slices, strings (por bytes), maps "
        "(por key) y canales (por valor). Se puede obtener el indice y/o "
        "el valor; para descartar uno se usa el identificador en blanco: "
        "`for i, _ := range s` o `for _, v := range s`."),
    21: ("Go permite funciones con multiples valores de retorno. La "
        "convencion es devolver un error como ultimo valor: "
        "`value, err := Func()`. El llamador debe comprobar err. Esta "
        "capacidad simplifica muchos patrones comunes de manejo de errores "
        "y de datos parcialmente-calculados."),
    22: ("Los valores de retorno pueden nombrarse en la firma de la "
        "funcion. Un `return` sin operandos devuelve los valores nombrados "
        "actuales. Effective Go recomienda nombrar solo cuando ayuda la "
        "documentacion del comportamiento; no para todos los casos."),
    23: ("Una llamada `defer` se ejecuta justo antes de que la funcion "
        "devuelva. Las llamadas deferidas se apilan (LIFO): la ultima "
        "deferida es la primera en ejecutarse. Se usa para liberar "
        "recursos, cerrar archivos, desbloquear mutexes, etc."),
    24: ("`new(T)` asigna memoria zeroada y devuelve *T. `make(T)` crea "
        "slices, maps y channels con inicializacion interna y devuelve T "
        "(no *T). make solo aplica a estos tres tipos; new aplica a cualquier "
        "tipo. El resutado de new está inicializado a cero pero no configurado."),
    25: ("Los literales compuestos inicializan structs, arrays, slices y "
        "maps: `T{field: value}`. Para structs, nombrar los campos es "
        "recomendado para mayor claridad. Los literales pueden anidarse y "
        "se pueden omitir los indices para arrays y slices."),
    26: ("Un array en Go es una copia completa: semántica por valor. Pasar "
        "un array a una funcion copia todos sus elementos. Para evitar "
        "copias caras, se pasa un slice (que es un descriptor ligero) o un "
        "puntero al array (&[N]T{...})."),
    27: ("Un slice tiene longitud (len, elementos visibles) y capacidad "
        "(cap, elementos hasta el final del array subyacente). `append` "
        "crece el slice hasta cap; si la longitud supera la capacidad, se "
        "asigna un nuevo array y se copian los elementos."),
    28: ("Las matrices 2D se implementan como slices de slices "
        "(`[][]T`). Cada fila puede tener longitud independiente. No se "
        "requiere que todas las filas tengan la misma longitud, lo que "
        "diferencia de los arrays 2D tradicionales."),
    29: ("Leer de un map devuelve siempre un valor (el zero value si la key "
        "no existe). Para distinguir key-ausente de valor-zero, usar el "
        "patron comma-ok: `v, ok := m[key]`. Si ok es false, la key no "
        "existe en el map."),
    30: ("`delete(m, key)` en un map es seguro: si la key no existe, no "
        "hace nada y no hay panic. No se necesita comprobar la existencia "
        "de la key antes de borrar. La funcion delete toma como argumentos "
        "el map y la key a eliminar."),
    31: ("El paquete `fmt` tiene variantes para cada destino: `Print/Printf` "
        "(stdout), `Fprint/Fprintf` (io.Writer), `Sprint/Sprintf` (string). "
        "Cada grupo usa verbs como `%v`, `%+v`, `%#v` para formatear "
        "valores de forma legible y para depuracion."),
    32: ("`append(slice, elementos...)` puede devolver un slice nuevo si la "
        "capacidad es insuficiente. Siempre se asigna el resultado: "
        "`s = append(s, x)`. Ignorar el retorno de append es un bug comun "
        "que conduce a datos perdidos."),
    33: ("Cada paquete puede tener funciones `init()` que se ejecutan "
        "automaticamente antes de `main()`. Se usan para validar o "
        "inicializar estado que no se puede expresar en una declaracion de "
        "variable. Puede haber varias funciones init por paquete y archivo."),
    34: ("Un metodo puede tener receiver por valor (T) o por puntero (*T). "
        "Si el metodo muta el receiver o se quiere evitar copias caras, use "
        "*T. La regla: no mezclar receiver por valor y por puntero en los "
        "metodos del mismo tipo; elige uno y aplica consistentemente."),
    35: ("Un tipo implementa una interfaz si satisface todos sus metodos. "
        "No se necesita `implements`. El tipado es estructural: si dos "
        "tipos tienen los mismos metodos, son equivalentes para esa "
        "interfaz. Esto permite interfaces pequeñas y reutilizables."),
    36: ("Las conversiones cambian el tipo de un valor: `T(v)`. Son "
        "seguras si el valor es compatible con T. No son lo mismo que "
        "las aserciones de tipo, que se aplican a interfaces y pueden "
        "fallar en tiempo de ejecucion."),
    37: ("Un type switch es una construccion switch que descubre el tipo "
        "dinámico de una interfaz. `switch v := x.(type)` asigna v con el "
        "tipo de cada caso, simplificando cadenas de aserciones. Cada "
        "caso puede comparar contra un tipo concreto."),
    38: ("El identificador en blanco `_` descarta valores. Se usa en "
        "asignaciones multiples para ignorar valores no usados: "
        "`_, err := f()`. No se puede leer de `_`; su unico proposito es "
        "descartar. También se usa para asignaciones de longitud fija que "
        "deben servir de documentacion."),
    39: ("Si un paquete se importa solo por sus efectos secundarios o si "
        "una variable no se usa, usar `_` para silenciar el error de "
        "compilacion: `import _ \"pkg\"` o `var _ = valor`. El compilador "
        "exige que todo import y toda variable local sea usada; el "
        "identificador en blanco es la forma de deshacerse del requisito."),
    40: ("Importar un paquete solo por sus efectos secundarios (registro "
        "de drivers, inicializacion de estado global): `import _ \"pkg\"`. "
        "El underscore suprime el error de 'imported and not used' y "
        "garantiza que se ejecute el paquete por sus efectos."),
    41: ("Para garantizar en tiempo de compilacion que un tipo implementa "
        "una interfaz, usar: `var _ Interface = (*Tipo)(nil)`. Si el tipo "
        "no implementa la interfaz, hay un error de compilacion. El "
        "identificador en blanco evita que la variable se use, pero el "
        "check sigue funcionando."),
    42: ("Un struct puede contener un tipo como campo anonimo (embedding). "
        "Los metodos del tipo embebido se promueven al struct que lo "
        "contiene, como si fueran propios. Las interfaces tambien pueden "
        "embeber otras interfaces, combinando metodos."),
    43: ("El mantra de Go: 'No comuniques compartiendo memoria; comparte "
        "memoria comunicate'. Los goroutines se comunican a traves de "
        "canales, no a traves de memoria compartida. Este enfoque evita "
        "condiciones de carrera y hace el comportamiento predecible."),
    44: ("Una goroutine es una funcion que corre concurrentemente con "
        "otras. `go f()` lanza una goroutine. Las goroutines se "
        "multiplexan sobre hilos del OS, son muy ligeras (memoria inicial "
        "pequena) y el runtime de Go gestiona su planificacion."),
    45: ("`recover()` detiene un panic y devuelve el valor del panic. "
        "Solo es util dentro de una funcion deferida: si se llama "
        "afuera de una defer, no hace nada. Se usa para convertir panics "
        "en errores devuelta, a menudo en servers que no deben caer."),
}

SOURCE = {
    'slug': 'effective-go',
    'title': 'Effective Go',
    'author': 'The Go Authors (go.dev/doc/effective_go)',
    'file': 'go.dev/doc/effective_go',
    'pages': 1,
    'extracted_with': ('triaje estructurado sobre las tecnicas de formato, '
                       'nombrado, error y concurrencia de Effective Go, '
                       'triadas a mano en pilas A (3, instrumented), B (6) '
                       'y C (36). NO ES UN VOLCADO LITERAL del documento; es '
                       'la interpretacion de cada tecnica como una invariante '
                       'contractable o de conocimiento. El porcentaje de '
                       'cobertura instrumentada es 3/45.'),
    'tags': ['fuente', 'documentacion', 'go', 'effective-go'],
    'corpus': (
        '45 tecnicas de Effective Go triadas a mano en pilas A (3, '
        'instrumented), B (6, no-especificables con why_not) y C (36, '
        'conocimiento). Las 3 de pila A miden invariantes de texto en .go '
        'con regex (tabs no espacios, sin parentesis en control, llave en '
        'misma linea). Las 6 de pila B son convenciones con una propiedad '
        'proxy pero que requieren analisis semantico o de flujo de datos. '
        'Las 36 de pila C son politicas y convenciones del toolchain gofmt '
        'que no tienen invariante de texto localizable. NO ES UN VOLCADO '
        'LITERAL del documento; es la interpretacion de cada tecnica como '
        'invariante contractable o de conocimiento.'
    ),
    'index': 'La pagina de indice lista los 45 nodos de este libro. Cada '
             'nodo enlaza su invariante a la fuente (fuente.md) que lo '
             'documenta.',
}

LOCATOR = 'go.dev/doc/effective_go'

TYPE = 'Concept'


def _etiquetas(idx):
    if idx in A_NODES:
        return ['effective-go', 'go', 'contractable', 'instrumented']
    if idx in B_NODES:
        return ['effective-go', 'go', 'no-especificable']
    return ['effective-go', 'go', 'conocimiento']


def build():
    """Devuelve el dict {source, nodes} con 45 nodos triados (eg01..eg45)."""
    nodes = []
    for idx in range(1, 46):  # eg01..eg45
        pile = ('A' if idx in A_NODES
                else 'B' if idx in B_NODES
                else 'C')
        node = {
            'id': 'eg{:02d}'.format(idx),
            'title': TITULOS[idx],
            'description': DESCRIPCIONES[idx],
            'type': TYPE,
            'tags': _etiquetas(idx),
            'pile': pile,
            'verification': 'instrumented' if idx in A_NODES else 'none',
            'locator': LOCATOR,
            'alias': ALIAS.get(idx, []) if pile in ('A', 'B') else [],
            'links': [],
        }
        if idx in A_NODES:
            regla = A_NODES[idx]
            node['instrument'] = 'effective_go_checks.py --rule {}'.format(regla)
            node['threshold'] = THRESHOLD[regla]
        if idx in B_NODES:
            node['why_not'] = WHY_NOT[idx]
        nodes.append(node)
    # Sanity: todos los 45 indices estan triados.
    return {'source': SOURCE, 'nodes': nodes}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--out', default='books/effective-go.json',
                        help='destino JSON del libro triado')
    args = parser.parse_args(argv)

    try:
        spec = build()
    except Exception as exc:
        print('NO-VERIFICABLE: {}'.format(exc))
        return 2

    total = len(spec['nodes'])
    if total != 45:
        print('ERROR: se esperaban 45 nodos y se emitieron {}'.format(total))
        return 1

    try:
        out_dir = os.path.dirname(os.path.abspath(args.out))
        os.makedirs(out_dir, exist_ok=True)
        with open(args.out, 'w', encoding='utf-8') as fh:
            json.dump(spec, fh, ensure_ascii=False, indent=2)
            fh.write('\n')
    except OSError as exc:
        print('NO-VERIFICABLE: no se pudo escribir {}: {}'.format(
            args.out, exc))
        return 2

    a = sum(1 for n in spec['nodes'] if n['pile'] == 'A')
    b = sum(1 for n in spec['nodes'] if n['pile'] == 'B')
    c = sum(1 for n in spec['nodes'] if n['pile'] == 'C')
    print('OK: libro effective-go emitido ({} nodos: A={}, B={}, C={})'.format(
        total, a, b, c))
    return 0


if __name__ == '__main__':
    sys.exit(main())
