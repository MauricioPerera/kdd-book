# kdd-book

Deconstruye un libro tecnico en dos cosas: **conocimiento** (un grafo de nodos
OKF) y **utilidad verificada** (contratos hibridos OKF+CCDD que se pueden
ejecutar).

Verificado contra los validadores reales del repo
[KDD](https://github.com/MauricioPerera/KDD), no contra una imitacion.

```
extraccion -> build_<libro> -> okf_emit ------> validate_okf              exit 0
                                    \
                                     -> contract_emit -> validate_contracts     exit 0
                                                      -> validate_test_commands exit 0
```

## Que produjo

Quince fuentes, 727 nodos, 151 contratos ejecutables, 155 instrumentos en
diecisiete familias. Los cuatro gates en verde: `validate_okf`,
`validate_contracts`, `validate_test_commands` y las 304 pruebas propias.

| Fuente | items | contractable | `instrumented` | con script | ejercicios |
|---|---|---|---|---|---|
| PEP 8 (G. van Rossum et al.) | 42 | 69,0% | **69,0%** | 29 | 26 |
| The Twelve-Factor App (A. Wiggins) | 16 | 62,5% | **62,5%** | 10 | 8 |
| Google developer documentation style guide | 80 | 52,5% | **52,5%** | 42 | 42 |
| Codigo Limpio (R. C. Martin) | 66 | 48,5% | **48,5%** | 31 | 28 |
| Tailwind CSS Docs (seleccion curada)\* | 21 | 47,6% | **47,6%** | 10 | 10 |
| Arquitectura Java solida (C. Alvarez Caules) | 33 | 45,5% | **45,5%** | 15 | 6 |
| Scrum y eXtreme Programming (E. Bahit) | 153 | 25,5% | **14,4%** | 17 | 4 |
| Stripe API Reference (seleccion curada)\*\* | 7 | 28,6% | **28,6%** | 2 | 2 |
| Semantic Versioning 2.0.0 (seleccion curada)\*\*\* | 11 | 27,3% | **27,3%** | 3 | 3 |
| WCAG 2.2 (W3C) | 104 | 11,5% | **11,5%** | 12 | 10 |
| htmx ~ Documentation | 59 | 10,2% | **10,2%** | 6 | 6 |
| Effective Go\*\*\*\*\* | 45 | 6,7% | **6,7%** | 3 | 3 |
| Rust API Guidelines Checklist\*\*\*\* | 54 | 5,6% | **5,6%** | 3 | 3 |
| The Zen of Python (PEP 20)\*\*\*\*\*\* | 19 | 0,0% | **0,0%** | 0 | 0 |
| The Agile Manifesto\*\*\*\*\*\*\* | 17 | 0,0% | **0,0%** | 0 | 0 |
| **Total** | **727** | **206** | **189** | **183** | **151** |

\* El numero de Tailwind **no es comparable** con el resto de la tabla. Las
otras ocho son un volcado literal de titulos; Tailwind es una seleccion hecha a
mano de 13 paginas sobre un sitio de ~210, donde el 93% restante es referencia
de clases CSS sin tecnica que prescribir. El detalle esta mas abajo.

\*\* El numero de Stripe **es el caso mas extremo de los tres**, y tampoco es
comparable. Es una seleccion de 7 paginas conceptuales ("Using the API") sobre
un sitio de ~750, donde el resto es el arbol completo de recursos (Charges,
Customers, PaymentIntents...) sin ninguna pagina prescriptiva. Sobre el sitio
completo el numero seria muchisimo mas bajo que el de Tailwind. El detalle esta
mas abajo.

\*\*\* SemVer es una seleccion de los 11 articulos numerados del spec completo
—no hay nada que recortar, la fuente entera son 11 articulos—, asi que aca "no
comparable" no es por tamano de muestra sino por genero: es una norma tecnica
corta y densa, no documentacion de referencia con paginas de relleno. Es
ademas la primera fuente construida por un agente externo (Poolside) sin
supervision de triaje, verificada de punta a punta despues. El detalle esta
mas abajo.

\*\*\*\* Rust API Guidelines Checklist es el numero mas bajo de la tabla, y es
el resultado esperado y correcto, no un defecto: de sus 54 items, la mayoria
pide entender semantica de Rust -si un trait object es object-safe, si un tipo
es realmente un smart pointer- que ningun instrumento de texto puede verificar
de verdad sin un compilador. Segunda fuente construida por Poolside, la
primera sobre un artefacto que no es Python (codigo Rust) y 5 veces mas grande
que SemVer. El detalle esta mas abajo.

\*\*\*\*\* Effective Go es la primera fuente sobre **prosa narrativa corrida**,
no un checklist ni un spec numerado: 15 secciones y mas de 30 subsecciones sin
items que enumerar. Tercera fuente construida por Poolside. Su primera entrega
cubria solo 10 de las 45 tecnicas identificables -una muestra sin avisar que
no era exhaustiva- y se le pidio expandir el grafo al documento completo antes
de aceptarla. Varias convenciones quedan en pila C por un motivo nuevo para
este repositorio: `gofmt` ya las hace cumplir, asi que no hay nada que el
codigo pueda violar de forma persistente. El detalle esta mas abajo.

\*\*\*\*\*\* The Zen of Python es la contraparte deliberada de las cuatro
fuentes anteriores: 0,0% instrumentado, y **eso es el resultado correcto, no
un fracaso del triaje**. Sus 19 aforismos son juicio estetico de diseno, no
umbrales binarios. Cuarta fuente construida por Poolside, y la primera donde
tuvo que decidir **no** instrumentar nada -incluido rechazar explicitamente
reusar un instrumento existente (`arch_checks.excepciones`) por generar
falsos positivos que tergiversarian al autor-. Sin pila A, los gates 2-4 no
aplican: solo corre `okf_emit`/`validate_okf`. El detalle esta mas abajo.

\*\*\*\*\*\*\* The Agile Manifesto es la segunda fuente sin pila A, y de un
genero distinto al Zen: 4 valores + 12 principios sobre **proceso de
equipo**, no diseno de codigo. Quinta fuente construida por Poolside.
Considero seriamente reusar `git_checks.py --rule cadencia` -que la fuente
hermana Scrum y XP ya usa para una tecnica parecida- para los principios de
entrega frecuente, y lo descarto con tres razones documentadas: sin `.git`
el checkout da NO-VERIFICABLE, la regla mide solo el hueco entre tags (no
la ventana de tiempo del principio ni "software funcionando"), y es un
subconjunto parcial de una propiedad que exige juicio de equipo. El detalle
esta mas abajo.

Cinco de las ocho no son libros, y estan para probar hasta donde llega el metodo.
La documentacion de htmx cae al 10,2% por una razon distinta a la de Scrum —no
habla de personas, habla de codigo— pero **describir una API no es prescribir
una tecnica**, y por eso casi la mitad cae en pila C por definicion del genero.

Los doce factores van al otro extremo por el motivo simetrico: **un manifiesto
es prescripcion pura**, sin una linea de relleno, y da el porcentaje mas alto de
las seis. Se sumo con una prediccion hecha antes de triajar y escrita en el
script de build: si la contractabilidad la decide que el autor haya
operacionalizado la tecnica, un documento asi tiene que quedar por encima de los
libros de codigo. Quedo. Sobre los doce factores solos, sin el preambulo, es
**10 de 12**.

Su corpus es el mas chico —16 titulos— y no por muestreo: cada factor es una
pagina con titulo, bajada y sin subsecciones, comprobado pagina por pagina. Con
n=16 cada item vale 6,3 puntos, asi que el porcentaje es real pero la precision
implicita no.

**La guia de estilo de Google entro para aislar una variable, y me equivoque.**
PEP 8 dio el numero mas alto y la explicacion que el grafo daba era el genero.
Pero PEP 8 cambia dos cosas a la vez respecto de un libro: el genero **y** el
tipo de propiedad, que en su caso es forma superficial de un archivo. Esta
fuente deja el genero fijo —es otra guia de estilo—, deja el artefacto al
alcance —texto plano, tan legible como un `.py`— y cambia solo el dominio: aca
se prescribe sobre prosa. La prediccion escrita antes de triajar fue **entre 20%
y 45%**. Dio **52,5%**, arriba de Codigo Limpio.

Lo que explica el fallo esta adentro de la propia fuente, sin necesidad de
comparar con ninguna otra:

| Seccion de la guia de Google | `instrumented` |
|---|---|
| Formato y organizacion | 75,0% |
| Puntuacion | 72,7% |
| Enlaces | 66,7% |
| Interfaces de computadora | 57,1% |
| Lengua y gramatica | 46,7% |
| Principios generales | 36,4% |
| Introduccion | 0% |

La guia se parte sola: **lo tipografico y lo lexico arriba, lo semantico abajo**.
Coma serial, raya sin espacios, cero "and/or", cero "(s)", segunda persona,
encabezados en minuscula, unidades separadas del numero — todo eso se cuenta.
"Voz y tono", "audiencia global", "evitar el antropomorfismo", "parrafos cortos"
— nada de eso se cuenta. El genero no era el motor: era un correlato, porque las
guias de estilo tienden a prescribir propiedades lexicas.

**PEP 8 entro con dos predicciones y la segunda se equivoco**, que es lo que la
hace valer la pena. La primera: una guia de estilo escrita para que la revise una
herramienta tenia que quedar arriba de los libros de codigo. Quedo — **69,0%, el
mas alto de las siete**. La segunda: iba a ser la primera fuente con reuso alto
de instrumentos, porque habla del mismo artefacto que Codigo Limpio y hay 22
reglas ya escritas esperando. **De sus 29 tecnicas medibles, dos reusan una regla
existente.** Que pasa con eso esta en el hallazgo 3.

Su corpus subestima, al reves que los otros seis: "Programming Recommendations"
es un solo titulo que adentro trae quince reglas concretas y medibles —comparar
con `is None`, no usar `except` pelado, `isinstance` en vez de comparar tipos— y
cuenta como un nodo, en pila B, porque una seccion cajon no tiene un umbral. Con
un corpus por regla en vez de por titulo, el 69% seria mas alto.

**WCAG entro para refutar, no para confirmar**, y es la fuente que corrigio el
hallazgo 2. Sus criterios se llaman literalmente *"testable success criteria"*:
estan operacionalizados al maximo por diseno, con umbrales numericos explicitos
—4.5:1 de contraste, 24 por 24 pixeles de area de toque— y su artefacto es HTML,
que este repositorio ya sabe leer. Si "el autor lo operacionalizo" fuera toda la
explicacion, tenia que dar altisimo. La prediccion escrita antes de triajar, en
el script de build, fue que iba a dar **bajo**; si daba mas de 60%, el
refinamiento estaba mal. Dio **11,5%**, y **13,8%** sobre los criterios solos.

Ademas: 17 tecnicas `proxy`, 233 en pila B (tecnica real sin propiedad medible)
y 288 en pila C (conocimiento). 39 enlaces cruzan de una fuente a otra.

Hay 206 tecnicas en pila A y 151 ejercicios, y la diferencia no es un pendiente:
**la cobertura se cuenta por regla, no por nodo**, porque un instrumento no
mejora por ejercitarse dos veces. DRY aparece en cinco nodos de tres fuentes y
las cinco corren `checks.py --rule g5`: un ejercicio las cubre. **Toda regla
cuyo instrumento admite la forma de ejercicio lo tiene**, y eso no se afirma de
memoria: `test_cobertura` compara el conjunto exacto y falla tanto si falta un
ejercicio como si sobra una excepcion declarada.

**La fraccion que decide el ruteo es `instrumented`, no la contractable.** La
diferencia es si el instrumento lee el artefacto del que trata la tecnica
—codigo, build, historial— o un registro que llena una persona —un tablero, un
diario—. Un umbral sin instrumento que lo lea sobre el objeto real es una
intencion, no un contrato.

## Por que estos numeros son una medicion y no una seleccion

El corpus de cada libro es una **lista cerrada del autor**, no una eleccion del
triaje: las 66 heuristicas enumeradas del capitulo 17 de Codigo Limpio, los 161
marcadores que Bahit dejo en su PDF. Si el pipeline eligiera que cuenta como
tecnica, el porcentaje seria una opinion.

Lo que no es tecnica **se cuenta igual**, en pila C. Descartar las tecnologias
(HTML, JSP, Hibernate) o los bullets de contexto inflaria el resultado.

Dos advertencias que viajan con su fuente. **htmx es el corpus mas debil de los
cuatro**: documentacion de referencia, cuyos 59 items son titulos de seccion
extraidos del PDF por tamano de fuente porque no traia marcadores. Es estructura
del autor, si, pero de un documento cuyo proposito no es enumerar tecnicas.

**Arquitectura Java tiene corpus mas debil** que los otros dos libros. Es un tutorial progresivo sin lista cerrada de conclusiones, y sus 33
items salieron de titulos de capitulo identificados por el triaje. n es menor y
las barras de error mas anchas. Esta dicho tambien en su nodo de procedencia,
no solo aca.

**Tailwind rompe la regla del titulo de esta seccion, y a proposito.** Su
corpus **es una eleccion del triaje**, no una lista cerrada del autor: de las
~210 paginas del sitio se eligieron a mano las 13 de "Getting started" y "Core
concepts" porque parecian prescriptivas, y de ahi salieron 21 tecnicas. El 47,6%
que da esa fuente mide la fraccion contractable **de esa seleccion**, no del
sitio — sobre las ~210 paginas completas el numero seria mucho mas bajo que el
de htmx, porque el 93% restante es referencia de clases CSS (`z-index`,
`flex-basis`...) sin tecnica que prescribir, mas extremo que la mitad de htmx
que cae en pila C. Se dejo entrar de todos modos porque el punto no era medir
el genero "documentacion de framework": era ver si, adentro de un sitio
dominado por referencia, la porcion que si prescribe se comporta como las otras
ocho fuentes. Se comporta: aparecen los mismos dos pares correcto/incorrecto
escritos por el autor que ya daban WCAG y PEP 8.

## Los hallazgos

### 1. La distribucion es bimodal, no un gradiente

Diez fuentes medidas (las ocho del grafo, mas Proyectos Agiles con Scrum y
Habitos Atomicos) dan 69%, 62,5%, 52,5%, 48%, 45%, 14%, 11,5%, 10%, 3,4% y 0%
de `instrumented`. Pero el 14,4% de Scrum y XP **no es un valor intermedio**: es
el promedio ponderado de dos poblaciones.

| Seccion de Scrum y XP | `instrumented` |
|---|---|
| Refactoring | 55% |
| TDD | 40% |
| Integracion continua | 29% |
| XP y Coding Dojo | 13% |
| Introduccion y agilismo | 3% |
| Scrum · Combinar · Kanban | 0% |

Ninguna seccion cae en el medio. Por eso **el ruteo se decide por seccion, no
por libro**: un numero a nivel libro mandaria todo a "solo grafo OKF" y tiraria
el capitulo de Refactoring, que da contratos tan buenos como los de Codigo
Limpio.

Durante cinco fuentes el eje parecio ser el **genero**: manifiesto arriba, libro
de codigo, libro de proceso, referencia de API abajo. La octava lo desarmo, y de
la manera mas util — dejando el genero fijo. La guia de estilo de Google es del
mismo genero que PEP 8 y su artefacto es igual de legible, y aun asi dio 52,5%
contra 69%. Lo unico que cambio fue **sobre que se prescribe**.

Y la propia guia de Google lo muestra sin salir de ella: su seccion de puntuacion
da 72,7% y la de formato 75,0%, mientras que la de principios generales da 36,4%
y la introduccion 0%. **Lo tipografico y lo lexico arriba, lo semantico abajo**,
adentro de un solo documento y de un solo autor.

Asi que el eje no es el genero ni el dominio ni el artefacto: es **la naturaleza
de la propiedad**. Lexica o estructural se mide; semantica no. El genero era un
correlato —una guia de estilo tiende a prescribir sobre tipografia, un libro de
proceso sobre personas— y por eso ordenaba bien hasta que aparecio un caso que
separaba las dos cosas.

Con eso los numeros raros dejan de serlo. WCAG da 11,5% no por ser norma sino
porque casi todos sus criterios piden juzgar sentido —una alternativa
"equivalente", un titulo que "describe el tema"—. Los doce factores dan 62,5% con
un dominio de infraestructura, tan lejos del AST como Scrum, porque lo que
prescriben es estructural: hay un manifiesto, hay un manejador de SIGTERM, hay
una linea de `Vary`.

### 2. La contractabilidad la decide si el autor operacionalizo la tecnica, y ademas si el umbral compara algo que esta en el artefacto

No la decide la tecnica ni el dominio. El grafo lo demuestra con dos casos, y en
sentidos opuestos:

- `scrum-xp/142` (expresiones extensas) -> `codigo-limpio/g19` (usar variables explicativas).
  **Misma refactorizacion, pilas distintas.** Martin la deja sin umbral —dice que
  conviene siempre mas y que es dificil excederse— y ademas exige nombres
  descriptivos, que es la mitad no medible. Bahit la deja medible porque su
  ejemplo extrae a `$a`, `$b`, `$c`, `$d`: al no reclamar nada del nombre, solo
  queda la reduccion de complejidad, que un parser cuenta.
- `arquitectura-java/08` (el principio SRP) -> `codigo-limpio/g30` (las funciones solo deben hacer una cosa).
  Otra vez el mismo principio en pilas distintas, ahora con los papeles
  cambiados: Martin cuenta operaciones semanticas y nunca da un numero; Caules lo
  aplica como separacion de capas, que es una regla de imports.

Que el caso aparezca dos veces en sentidos opuestos es lo que lo vuelve un
patron y no una anecdota. Y solo se puede afirmar con los dos nodos a la vista:
**por eso el grafo tiene enlaces entre libros y no es una tabla por libro**.

**La segunda mitad del titulo la agrego WCAG, y es una correccion.** Durante
cinco fuentes el hallazgo decia solo que la contractabilidad la decide la
operacionalizacion, y WCAG entro justamente para poder desmentirlo: es la fuente
mas operacionalizada de las seis y da 11,5%.

La diferencia esta en que quiere decir "testable" para el W3C: **que una persona
formada pueda decidir si se cumple**. Eso no es lo mismo que medible, y la
distancia no es de grado. 1.1.1 pide una alternativa textual que cumpla "el
proposito equivalente": que el `alt` este es decidible, que sea equivalente no lo
decide ninguna medicion, y *equivalente* es la palabra del criterio. Lo mismo con
2.4.2 (un titulo que "describe el tema"), 2.4.4 (el proposito del enlace en su
contexto) y 2.4.6. Son criterios impecables y ninguno es un umbral sobre el
artefacto: son juicios sobre el **contenido**.

Los 12 que si son medibles se distinguen por una sola cosa: el autor nombro un
**mecanismo** decidible —un token de `autocomplete`, un `lang` bien formado, un
`role` con nombre accesible, el texto visible contenido en el nombre accesible—
en vez de una cualidad del contenido.

Y hay un caso que separa las dos condiciones con una nitidez que no se consigue
inventando ejemplos. Contraste (1.4.3, 1.4.6) y area de toque (2.5.5, 2.5.8)
tienen **los umbrales mas nitidos de los 87** —una razon de 4.5:1, un area de 24
por 24— y aun asi no se miden leyendo el HTML: comparan valores **renderizados**.
Umbral perfecto, artefacto fuera de alcance. Quedan en pila A porque el proyecto
puede declarar esos valores, que es la misma salida que uso `http_checks` para no
salir a la red — pero muestran que operacionalizar no alcanza si lo que el
umbral compara no esta donde se puede leer.

El par que mejor lo ilustra cruza dos fuentes y describe **la misma pagina
rota**. `wcag/sc2-1-1` (Keyboard) y `htmx/20` (mejora progresiva) hablan del
mismo defecto: un `<div hx-get>` no es un enlace ni un boton, asi que ni degrada
sin javascript ni se puede operar con el teclado. htmx pide un `<a href>` o un
`<form action>` —un mecanismo, y esta en pila A—; WCAG pide que "toda la
funcionalidad sea operable por teclado" —un resultado, y esta en pila B—. No es
que un criterio sea mejor: **el que nombra el mecanismo se puede instrumentar**.

La septima sumo algo que el grafo no tenia todavia: **dos autores que se
contradicen**. J1 de Codigo Limpio aconseja usar imports con comodin para evitar
listas largas; PEP 8 los prohibe porque borran que nombres entran al espacio de
nombres. J1 estaba en el grafo sin instrumento y con su motivo declarado —
implementarla invirtiendo el consejo seria tergiversar al autor—. Con PEP 8
adentro la contradiccion deja de ser una nota al pie y pasa a ser un enlace: dos
nodos, dos autores, umbrales opuestos sobre el mismo artefacto, y el grafo los
sostiene **sin elegir**. Es la misma politica que la fusion de memorias, donde un
desacuerdo de triaje se reporta y no se resuelve.

La quinta fuente sumo un tercer caso, y esta vez con un umbral que no admite
interpretacion: `doce-factores/f03` (guardar la config en el entorno) contra
`codigo-limpio/g35` (mantener los datos configurables en los niveles
superiores). **Misma idea, pilas distintas otra vez.** Martin la deja en pila B
porque que dato conviene subir es un juicio; Wiggins fija cual es el nivel
superior —el entorno— y da el umbral con un test que se puede correr: *si el
repositorio no se pudiera abrir hoy sin filtrar credenciales, esta en rojo*.

DRY aparece en los tres libros de codigo y los tres autores la operacionalizan:
los tres nodos son contractables y comparten instrumento.

### 3. El metodo transfiere; los instrumentos no

Probar el pipeline sobre documentacion de htmx dio 10,2% medible, y las seis
tecnicas medibles resultaron leer **HTML, HTTP o plantillas**. Ninguna de las 39
reglas que habia servia: todas parsean AST de Python o corren comandos.

El triaje, el criterio de pila, la regla de ruteo por seccion y la forma del
contrato funcionaron igual. Lo que no transfiere es **la capa de medicion, que
esta atada al lenguaje del artefacto**. De ahi salieron tres familias nuevas
—`html_checks`, `http_checks` y `template_checks`— y con ellas las seis quedaron
cubiertas.

Era parcialmente visible con J1 y J2, que quedaron afuera por ser de Java. Aca
el efecto fue total, porque cambio el artefacto entero.

La quinta fuente lo confirmo desde otro angulo y sumo una cuarta familia. Los
doce factores tambien hablan de proyectos en Python, asi que el lenguaje no era
el problema: **cambio el artefacto**. Sus reglas no leen el AST de un archivo ni
ejecutan el proyecto, leen su forma —el manifiesto, el punto de entrada, los
archivos de despliegue— y por eso **ninguna de las 45 reglas que ya habia
servia tampoco**: hubo que escribir ocho en una familia nueva, `entorno_checks`,
y dos mas en `git_checks`, que tenia el artefacto correcto pero no las
propiedades. La conclusion se afina: lo que no transfiere no es la capa de
medicion **por idioma** sino **por artefacto**.

**Y la septima corrigio tambien eso**, con un numero que despues quedo a la
vista al escribir los instrumentos: `pep8_checks` tiene **27 reglas** y es la
familia mas grande del repositorio, mas que las 22 de `checks.py`. PEP 8 entro con la prediccion de que iba a
ser la primera fuente con reuso alto: habla del **mismo artefacto** que Codigo
Limpio —el AST y el texto de un archivo Python— y habia 22 reglas escritas
esperandola. De sus 29 tecnicas medibles, **dos** reusan una regla existente.

El motivo se ve poniendo las dos listas al lado: `checks.py` mide duplicacion,
numeros magicos, codigo muerto, envidia de caracteristicas —habla de
**estructura y significado**—; PEP 8 mide sangria, lineas en blanco, orden de
imports, CapWords —habla de **forma superficial**—. Mismo lenguaje, mismo
artefacto, misma clase de prescripcion, y los instrumentos no se tocan.

Asi que la conclusion se afina una vez mas: lo que no transfiere no es el idioma
ni el artefacto, es **la propiedad que se mide**. Compartir artefacto no es
compartir medicion, y es la razon por la que diez familias de instrumentos no
son diez formas de hacer lo mismo.

La unica coincidencia real es instructiva por si sola: G24 de Codigo Limpio se
llama "seguir las convenciones estandar" y su instrumento ya media largo de
linea, tabuladores y espacios al final. **G24 ya era un pedazo de PEP 8 sin
decirlo**: Martin nombra la convencion y delega en el equipo cual es; PEP 8 es
esa convencion escrita.

### 4. Los principios de arquitectura son tan medibles como las heuristicas de codigo

Prediccion razonable para Arquitectura Java: mismo artefacto que Codigo Limpio
pero tecnicas mas semanticas, o sea resultado intermedio. Salio 45,5%, casi
igual. La razon no es obvia: **son propiedades del grafo de dependencias e
instanciacion**, que es lo que el analisis estatico lee de forma nativa.
"Semantico" para un humano no implica "no medible" para un parser.

### 5. El autor que se molesta en escribir el error real hace el trabajo del oraculo

Dos tecnicas de la seleccion curada de Tailwind traen, en el propio texto de la
documentacion, un ejemplo del error **y** su correccion, uno al lado del otro:

- `working-mobile-first` — la guia escribe el anti-patron completo:
  `<div class="sm:text-center">` (centra solo desde 640px) contra
  `<div class="text-center sm:text-left">` (centra en mobile, alinea a la
  izquierda desde 640px). No hace falta inventar el caso rojo: el autor ya lo
  escribio como advertencia.
- `conflicting-utility-classes` explica por que dos utilidades que fijan la
  misma propiedad CSS no "se combinan": la que gana es la que queda mas tarde
  en la hoja generada, no la que esta mas a la derecha en el `class=""`. Es
  exactamente el tipo de propiedad —relacion entre dos elementos del mismo
  artefacto— que `checks.py` mide sobre Python (G33, condiciones de limite
  repetidas) y `pep8_checks` sobre nombres.

Es el mismo patron que ya daba WCAG con `sc2-1-1`/`htmx-20` —la misma pagina
rota descrita por dos autores—: **cuando el autor se toma el trabajo de
escribir el error real en vez de solo nombrar la regla, el oraculo del
ejercicio ya esta escrito**, solo hay que copiarlo. Encontrarlo en una fuente
elegida por seleccion humana y no por lista cerrada del autor sugiere que el
patron no depende de como se armo el corpus: depende de si el autor prescribio
con un ejemplo concreto o con una abstraccion.

## El idioma y la identidad de un nodo

De los 12 campos de un nodo, **2 dependen del idioma del libro y 10 no**:

| Depende del idioma | No depende |
|---|---|
| `title`, `description` | `id`, `type`, `tags`, `pile`, `verification`, `locator`, `links`, `instrument`, `threshold`, `alias` |

`alias` esta del lado estable a proposito: trae el nombre canonico en varias
lenguas a la vez (`ley de Demeter`, `law of Demeter`, `train wreck`), asi que no
depende de la edicion — es justamente el puente entre ellas.

**Los instrumentos son inmunes.** `chain_depth.py --max 1` no sabe en que idioma
se escribio el libro: mide el AST de Python. Y el contrato entre un agente y un
instrumento **es el exit code, no el mensaje** — los mensajes estan en espanol y
un agente en cualquier idioma consume 0/1/2 sin traducir nada.

El `id` esta en la columna estable, pero no siempre lo estuvo. Era el codigo del
autor pegado a un slug del titulo:

```
g36-evitar-desplazamientos-transitivos    <- edicion espanola
g36-avoid-transitive-navigation           <- edicion inglesa: OTRO nodo
```

Tres consecuencias, y **ninguna la detectaba nadie porque cada grafo validaba
perfecto por separado**: los enlaces entre libros dejaban de resolver, dos
grafos del mismo libro en idiomas distintos se duplicaban en vez de fusionarse,
y la memoria exportada no se podia juntar con la de otro.

Ahora el id es solo el identificador del autor —`g36`, `142`, `08`— y el titulo
una etiqueta que cambia con la edicion. La navegabilidad que daba el slug se
recupera donde corresponde: el nodo de procedencia de cada libro trae el indice
completo de titulos.

Falta una pieza mas para cruzar idiomas, y no se resuelve copiando texto. Cada
tecnica lleva un campo **`alias`** con su nombre canonico, que es metadato del
triaje y no del autor. Sin eso la memoria solo responde a las palabras que
eligio el traductor: `buscar demeter` no encontraba a G36, que en esta edicion
se llama "Evitar desplazamientos transitivos".

Lo tienen **337 de las 727**, y el reparto no es casual:

| Pila | Con alias | Regla |
|---|---|---|
| A (medibles) | **206 de 206** | exigido por prueba: son las que tienen instrumento y contrato, o sea las que un agente va a buscar |
| B (no medibles) | 128 de 233 | se completan las que tienen nombre reconocido |
| C (conocimiento) | 3 de 288 | no aplica: son temas, tecnologias y pasos de tutorial |

Las 77 de pila B que quedan afuera son, en su mayoria, criterios de WCAG cuyo
titulo **ya es el nombre canonico**: "Captions (Prerecorded)" o "Timing
Adjustable" no tienen otro nombre por el que alguien los busque, y su
identificador —2.2.1— es mas conocido que cualquier alias que yo les inventara.
Se completaron los 23 que si tienen nombre de uso corriente (*skip link*,
*focus visible*, *aria-live*). Las 14 restantes son subsecciones sin nombre
propio: nueve de Scrum y XP y cinco de htmx que nombran una combinacion de
atributos y no una tecnica. **Inventar un nombre canonico donde no lo hay seria
meter ruido en la busqueda**, que es lo contrario de lo que el alias existe para
hacer.

El alias es el handle que cruza idiomas **y libros**: `buscar DRY` devuelve las
cinco entradas de los tres libros de codigo, todas apuntando al mismo instrumento.

## La memoria portable

`memoria.py` exporta todo lo extraido a **un solo archivo** y lo hace
consultable. Es lo que otro agente necesita para usar este conocimiento **sin
tener los libros**.

```bash
python memoria.py exportar          # -> memoria.json: 727 tecnicas, 157 instrumentos
python memoria.py buscar DRY        # la misma tecnica en los tres libros
python memoria.py medibles          # las que tienen instrumento, con su comando
python memoria.py aplicar codigo.py # que de todo lo que se aplica a este codigo
python memoria.py fusionar a.json b.json -o c.json
```

El bundle son **735 KB**: `memoria.json` + `memoria.py` + `instruments/`.
Verificado: copiado a un directorio limpio, sin `books/`, sin `exercises/`, sin
PDF y sin el repo, `aplicar` corre **53 instrumentos** sobre un archivo
cualquiera y reporta los que estan en rojo con la tecnica que senala cada uno.

Que familia puede correr sobre que **lo declara cada familia**, en una constante
`ARTEFACTO`, y no una lista en `memoria.py`. La lista existio y quedo vieja: con
`pep8_checks` escrito —27 reglas que miden exactamente un archivo `.py` suelto—
`aplicar` siguio corriendo las mismas 26 de siempre sin que nada fallara. Es el
segundo defecto de esa forma en el mismo archivo, y por eso esta vez el dato vive
donde se sabe.

Cada tecnica exportada lleva su pila, su instrumento y su umbral, sus enlaces
—incluidos los que cruzan de libro—, su ubicacion en la fuente, su nombre
canonico y, si lo tiene, el contrato que la ejercita.

Lo que la hace portable es lo de la seccion anterior: **ids estables entre
idiomas** para que dos memorias se fusionen en vez de duplicarse, **exit codes**
en vez de mensajes como interfaz, y **alias** para que se pueda consultar sin
saber como la tradujo cada edicion.

### Fusionar dos memorias

Es lo que los ids estables habilitan, y lo mas facil de probar. Escenario: otra
persona triaja la **edicion inglesa** de Codigo Limpio — mismos codigos del
autor, titulos en ingles, todavia sin instrumentos escritos, y con un
desacuerdo: para ella G30 ("hacer una sola cosa") **si** es medible.

```
$ python memoria.py fusionar memoria.json otra-memoria.json -o fusionada.json
2 memoria(s), 793 entradas -> 727 tecnicas (66 fusionadas) en fusionada.json

2 conflicto(s) de triaje, sin resolver a proposito:
  codigo-limpio/g30          pila           'B' contra 'A'
  codigo-limpio/g30          verification   'none' contra 'instrumented'
```

Las 66 tecnicas de la edicion inglesa se fusionaron con las que ya estaban en
vez de duplicarse. `g36` quedo con el titulo espanol, el ingles sumado a sus
alias, y el instrumento que solo una de las dos memorias tenia.

**El mismo ejercicio con los ids viejos:**

| | entradas | resultado | conflictos |
|---|---|---|---|
| ids estables (`g36`) | 727 + 66 | **727 tecnicas** | **2 reportados** |
| ids con slug (`g36-evitar-...`) | 727 + 66 | 793 tecnicas | 0 |

Con slug no se fusiona nada: cada tecnica queda dos veces, una por edicion. Y
lo peor no es la duplicacion — es que **el desacuerdo de triaje sobre G30 no lo
ve nadie**, porque nada esta comparando las dos entradas.

Que hace la fusion con cada campo:

- el `titulo` de la primera memoria gana, y el de las demas **se guarda como
  alias**: un titulo en otro idioma es exactamente un nombre alternativo;
- `alias`, `enlaces` y `tags` se unen, ignorando caja y acentos para que
  `ley de Demeter` y `Ley De Demeter` no queden como dos;
- `instrumento` y `contrato` se completan si a una le falta y a otra no;
- una discrepancia en pila, verification, instrumento o umbral **no se
  resuelve**: se reporta y el comando sale con 1. Son juicios de triaje
  distintos, y elegir uno en silencio seria inventar un consenso que no existe.

## Uso

```bash
python build_codigo_limpio.py <texto-extraido.txt>       # -> books/codigo-limpio.json
python build_doce_factores.py                           # el volcado de titulos ya esta versionado
python okf_emit.py books/codigo-limpio.json --out out/knowledge
python contract_emit.py exercises --out out --book codigo-limpio

python <KDD>/scripts/validate_okf.py out/knowledge
python <KDD>/scripts/validate_contracts.py out/knowledge/contracts --repo-root out
python <KDD>/scripts/validate_test_commands.py out/knowledge/contracts out
```

`out/` no se versiona: se regenera entero desde `books/` y `exercises/`, sin
necesidad del PDF. Tres de las cinco fuentes ni siquiera lo necesitan para
reconstruirse: su volcado de titulos esta versionado.

## Piezas

| Pieza | Que hace | Determinista |
|---|---|---|
| extraccion | PDF -> texto UTF-8 o volcado de marcadores | si |
| `build_<libro>.py` | titulos del libro + el triaje declarado -> `books/<libro>.json` | si, dado el triaje |
| **triaje** | clasificar cada tecnica en pila A/B/C | **no: es juicio** |
| `okf_emit.py` | JSON -> arbol `knowledge/` que pasa `validate_okf` | si |
| `contract_emit.py` | ejercicios -> contratos que pasan los tres gates | si |
| `instruments/` | miden si la tecnica quedo aplicada | si |
| `memoria.py` | exporta el conocimiento a un archivo y lo hace consultable | si |

El triaje es la unica pieza con juicio y esta aislada a proposito: vive como
tabla legible en el script de build, auditable linea por linea.

## Los contratos

Dos restricciones del validador definen todo el diseno, y ninguna se ve hasta
leer su codigo:

**1. `budget` solo admite cuatro subclaves** — `cyclomatic_max`, `nesting_max`,
`lines_max`, `params_max`. Son las que lee el gate de nivel 2; cualquier otra es
error porque *el tope quedaria ignorado en silencio*. De las 32 heuristicas
contractables de Codigo Limpio **una sola mapea directo**. Las demas necesitan
instrumento propio.

**2. `test_command` corre con `shlex.split` sin shell**, asi que no admite `&&`.

De esas dos sale `instruments/gate.py`, que resulta ser el diseno correcto:

| Corre | Verifica | Si falla |
|---|---|---|
| oraculo congelado | no rompiste el comportamiento | `ORACULO ROJO` |
| instrumento | aplicaste la tecnica | `INSTRUMENTO ROJO` |

Hacen falta los dos y hay que saber cual fallo. **Una refactorizacion no cambia
el comportamiento observable, asi que el oraculo pasa igual antes y despues**: en
la mayoria de los ejercicios esta ciego y solo el instrumento discrimina. Si los
tests bastaran, no harian falta los instrumentos.

## Los instrumentos

155 reglas en diecisiete familias. Que varias tecnicas compartan una no es un atajo:
es que preguntan lo mismo.

| Familia | Reglas | Mide sobre | Ejemplo |
|---|---|---|---|
| `checks.py` | 22 | el AST de un archivo Python | duplicacion, numeros magicos, ley de Demeter |
| `repo_checks.py` | 7 | el proyecto entero | un comando para probar, cobertura, tiempo de suite |
| `arch_checks.py` | 6 | relaciones entre modulos | capas, instanciacion, ISP |
| `git_checks.py` | 5 | el historial | cadencia de entregas, ramas sin integrar, identificador de release |
| `entorno_checks.py` | 8 | la forma del proyecto | dependencias declaradas, config en el entorno, logs a stdout |
| `a11y_checks.py` | 10 | el DOM y valores renderizados | idioma, etiquetas, contraste, area de toque |
| `pep8_checks.py` | 27 | la forma de un archivo Python | sangria, lineas en blanco, imports, CapWords |
| `html_checks.py` | 3 | el DOM | mejora progresiva, token CSRF, indicador de request |
| `http_checks.py` | 2 | respuestas capturadas | `Vary: HX-Request`, politica de seguridad |
| `template_checks.py` | 1 | plantillas sin renderizar | interpolacion sin escapar |
| `prosa_checks.py` | 42 | un documento de prosa (Markdown u otro texto) | coma serial, encabezados, texto de enlace, alt de imagen |
| `tailwind_checks.py` | 10 | HTML/JSX con clases de Tailwind y CSS con `@theme` | utilidades en conflicto, mobile-first, namespace de color |
| `stripe_checks.py` | 2 | codigo Python que llama a la API de Stripe | claves embebidas en el codigo, Idempotency-Key en GET/DELETE |
| `semver_checks.py` | 3 | codigo Python que declara `__version__` | formato X.Y.Z, identificadores de pre-release, de build metadata |
| `rust_api_checks.py` | 3 | codigo Rust (.rs / Cargo.toml), leido como texto | getters por valor, `#[derive(Debug)]`, `?` en ejemplos rustdoc |
| `effective_go_checks.py` | 3 | codigo Go (.go), leido como texto | indentacion con tabs, sin parentesis en control, llave en la misma linea |
| `mutation_checks.py` | 1 | mutantes de limite | si la suite nota que un limite se corrio |

Tres decisiones que conviene tener a la vista:

- **`arch_checks` exige que el proyecto declare sus capas y su esquema.** Sin la
  declaracion sale con exit 2, no verde. Una regla de capas que el instrumento
  adivine no es una regla, es una opinion.
- **`git_checks` sigue siendo `instrumented`, no `proxy`**: git no lo llena nadie
  a mano. Es la diferencia con el tablero, que tiene timestamps automaticos pero
  contenido escrito por personas. Sobre `tddorden` conviene ser preciso: el
  historial conserva el **orden**, no el haber visto el test en rojo, y el
  instrumento no pretende que sea lo mismo.
- **`html_checks` existe porque el metodo transferia y los instrumentos no.**
  Al triajar la documentacion de htmx (59 titulos, 10,2% medible) las seis
  tecnicas medibles resultaron leer HTML, HTTP o plantillas, y **ninguna de las
  39 reglas que habia servia**: todas parsean AST de Python o corren comandos.
  El criterio de pila, la regla por seccion y la forma del contrato funcionaron
  igual; lo que no transfiere es la capa de medicion, que esta atada al lenguaje
  del artefacto. `html.parser` no devuelve un arbol, asi que se construye uno:
  las tres reglas preguntan por ancestros y sin arbol ninguna se puede escribir.
- **`http_checks` no sale a la red: lee capturas.** Las dos tecnicas hablan de
  lo que el servidor devuelve, y el proyecto prohibe red. La salida es la misma
  que con las capas: el proyecto **declara** el artefacto, en este caso
  intercambios capturados en el formato de la propia HTTP. Producirlos —un test,
  un `curl -v`, un proxy— es su responsabilidad.
  `vary` no adivina si la respuesta varia: **lo demuestra** comparando dos
  capturas de la misma ruta, una con `HX-Request` y otra sin el. Con una sola no
  hay nada que comparar y sale con exit 2, que es mas honesto que dar verde.
- **`template_checks` fue el ultimo, y el motivo es el mas instructivo.** El
  marcador de interpolacion sin escapar **cambia con cada motor**: en handlebars
  el escape se decide por interpolacion (`{{x}}` escapa, `{{{x}}}` no), pero en
  jinja2 y django se decide en la aplicacion y **desde la plantilla es
  invisible**. La misma plantilla es segura o no segun un dato que no esta
  escrita en ella. Asi que se pide: `--motor`, y `--autoescape` para los motores
  con estado global. Es la tercera vez que aparece la misma forma —las capas de
  `arch_checks`, las capturas de `http_checks`— y siempre por lo mismo: **cuando
  el dato que decide la medicion vive fuera del artefacto, se pide, no se
  supone.** Un instrumento que lo adivinara diria "limpio" sobre una plantilla
  que inyecta.
  Su docstring dice tambien lo que **no** mide: escapar para HTML no protege
  dentro de un `<script>` ni en un atributo sin comillas. Eso es escapado
  sensible al contexto y es otra tecnica; queda declarado para que el verde no
  se lea como mas de lo que es.
- **`entorno_checks` es la primera familia que no lee ni codigo ni ejecucion,
  sino la forma del proyecto.** Sus ocho reglas salen de los doce factores, pero
  lo que las junta es que miden: como se declara lo que la app necesita, como se
  expone, como se comporta como proceso. Es tambien la familia que mas dice lo
  que **no** ve: las reglas que buscan un marcador lexico —una credencial, un
  locator— encuentran lo que se escribe con las palabras de la convencion, y una
  clave asignada a una variable llamada `x` no la ve nadie. Eso no se arregla
  afinando la expresion regular: es el limite de leer el codigo en vez de
  ejecutarlo, y esta escrito en cada regla para que el verde no se lea como mas
  de lo que es.
  Su primer hallazgo fue contra este mismo repositorio, y fue un falso positivo
  propio: `daemonizar` marcaba cualquier llamada con un argumento terminado en
  `.pid`, asi que **la linea que hace la comprobacion se marcaba a si misma**.
  Preguntar si una ruta es un archivo PID no es escribirlo. Corrido contra el
  repo tambien encontro tres rojos legitimos —sin manejador de SIGTERM, sin
  puerto propio, sin manifiesto— que son correctos: esto es una biblioteca de
  instrumentos, no una app de doce factores.
- **`a11y_checks` es la unica familia donde el verde de mas hace dano.** Diez
  reglas para doce criterios: `contraste` y `toque` sirven a dos cada una, con
  el umbral por argumento, porque el autor da el mismo mecanismo en dos niveles
  de conformidad. Y su docstring dice lo que ninguna otra necesita decir tan
  fuerte: **verde no es "la pagina es accesible", es "estos doce mecanismos
  estan"**. Una herramienta de accesibilidad que da verde de mas convence de que
  no hay nada que revisar, y quedan afuera 75 criterios que son tecnicas reales.
  Reusa el arbol de `html_checks` en vez de construir otro, y para eso hubo que
  agregarle texto a los elementos: comparar la etiqueta visible contra el nombre
  accesible pide el texto, y las tres reglas de htmx solo miraban atributos. Dos
  parsers de HTML en el mismo repositorio terminan discrepando — ya paso una vez
  con la definicion de emisor de peticiones.
  Correr las diez de una pasada destapo un defecto propio: `contraste` y `toque`
  comparten `--min`, y 24 —que son pixeles— se leyo como una razon de contraste.
  **21:1 es el maximo posible**, negro sobre blanco, asi que ese umbral no lo
  cumple ninguna pagina: el instrumento se ponia rojo sobre paginas impecables
  sin dar ninguna pista. Ahora sale con exit 2 y nombra la regla que el que lo
  corrio probablemente queria.
- **`mutation_checks` escribe sobre el archivo que mide**, asi que tiene dos
  obligaciones extra con test propio: restaurarlo siempre, y salir con exit 2 si
  la suite ya venia en rojo — con la suite rota no se puede saber si mata
  mutantes o si falla sola.
- **`prosa_checks` es la primera familia que lee prosa en vez de codigo**, y la
  mas grande: 42 reglas, mas que las 27 de `pep8_checks`. Existe porque la
  octava fuente demostro que la naturaleza de la propiedad no depende del
  artefacto — lo lexico y lo tipografico se miden sobre un `.md` igual que
  sobre un `.py`, y lo semantico no se mide en ninguno de los dos. Seis reglas
  —terminos desaconsejados, nombres de producto, lenguaje inclusivo, jerga,
  posesivo sobre un producto, tipos de aviso— necesitan que el proyecto declare
  su vocabulario, la misma forma que `arch_checks` con las capas: la guia da el
  mecanismo, la lista es del proyecto.
  Blanquea bloques de codigo e inline code antes de medir, por el mismo motivo
  que `html_checks` blanquea `<script>`: un "e.g." dentro de un ejemplo de
  codigo no es una violacion de prosa, y un regex sin ese blanqueo no lo sabe.
  Saboteados los 42 mecanismos, los 42 tienen dientes. Corrida contra el propio
  repositorio via `pep8_checks`, la unica marca real fueron seis identificadores
  `l` en comprensiones — renombrados.
- **`tailwind_checks` es la primera familia sin parser real detras.** Ni de
  HTML ni de CSS: son expresiones regulares sobre el texto, igual que
  `html_checks` antes de tener un arbol. El mapa utilidad -> propiedad CSS que
  usan `utilidades-en-conflicto` y `mobile-first` es deliberadamente chico —
  cubre solo las familias que las propias paginas fuente usan de ejemplo
  (`display`, `position`, `text-align`...), ampliable con `--propiedades` — y
  la regla de utilidades removidas es angosta a proposito: solo mide las que
  la guia de actualizacion llama "removidas" (`bg-opacity-*`), no las
  "renombradas" (`shadow` -> `shadow-sm`), porque estas ultimas **siguen siendo
  clases validas en v4** con otra escala, y marcarlas seria adivinar si el
  autor migro a proposito o dejo el codigo a medio actualizar.
  `className={` de JSX usa llaves y no comillas, asi que el patron que detecta
  `class="..."`/`className="..."` no ve un template literal como
  `` className={`bg-${color}-600`} ``: hizo falta un segundo patron aparte
  para ese caso, que es ademas el mas comun de nombre de clase dinamico en
  React.
- **`stripe_checks` es la familia mas chica del repositorio: dos reglas**, y
  las dos son la contrapositiva de una prohibicion sin condicional del propio
  texto de docs.stripe.com/api. La otra mitad de "Idempotent requests" -usar
  una clave de idempotencia al crear o actualizar- es condicional ("cuando..."),
  no una prohibicion plana, y por eso no entro en el umbral: exigirla en cada
  POST hubiera sido inventar una regla que el texto no da sin condicion. Lee
  codigo Python via `ast`, igual que `entorno_checks`, y declara el mismo tipo
  de limite: una clave armada por concatenacion en vez de un literal no la ve
  nadie, y un header de idempotencia en una variable intermedia en vez de un
  dict inline en la llamada tampoco.
- **`semver_checks` es la primera familia construida por un agente externo**,
  no por mi. Poolside triajo los 11 articulos del spec de Semantic Versioning
  sin que nadie le dijera que pila le tocaba a cada uno, y eligio tres:
  formato `X.Y.Z` (articulo 2), identificadores de pre-release (articulo 9) y
  de build metadata (articulo 10). Las otras ocho —cero mayor, inmutabilidad,
  precedence— quedaron en B/C por el mismo criterio que aplican las otras
  catorce familias: juicio de proceso o conocimiento, no una propiedad
  medible. Sigue la misma convencion (`ast`, `ARTEFACTO`, `NoVerificable`,
  `RULES`) sin que se le haya pedido copiarla explicitamente, solo mostrandole
  el repositorio existente como ejemplo.
  La verificacion independiente encontro lo que el propio agente no reporto:
  en 2 de sus 3 ejercicios, el oraculo pedia solo que `__version__` fuera un
  string no vacio, sin exigir que siguiera declarando el sufijo pre-release o
  build correspondiente. Eso dejaba pasar el atajo que el spec del ejercicio
  prohibe explicitamente —sacar el sufijo en vez de corregirlo— sin que nada
  lo notara. Es el mismo tipo de hallazgo que ya aparecio dentro de este
  repositorio (`daemonizar` marcandose a si mismo, el `g4`/`g12` que se
  contradecian): un gate en verde no es lo mismo que un gate completo.
- **`rust_api_checks` es la primera familia sobre un artefacto que no es
  Python.** El checklist de Rust API Guidelines trae 54 items en 11
  categorias, y Poolside -la misma agente que hizo SemVer- lo triajo esta vez
  sola con la advertencia explicita de no forzar pila A sin propiedad medible
  de verdad. El resultado es honesto y bajo: A=3 (`C-GETTER`,
  `C-COMMON-TRAITS`, `C-QUESTION-MARK`), B=6, C=45. Los 51 items que quedaron
  afuera piden entender semantica de Rust -si un trait object es object-safe,
  si un tipo es realmente un smart pointer- que ningun regex puede verificar
  sin un compilador detras, y ese es justo el limite que se le pidio
  respetar. Lee texto `.rs`/`Cargo.toml` sin ningun parser real, igual que
  `tailwind_checks` o `html_checks` antes de tener un arbol.
  El self-audit del repositorio encontro seis defectos reales en el
  instrumento entregado -un import muerto, un numero magico por indexar un
  grupo de regex sin nombre (`.group(3)`, corregido a `.group('retorno')`),
  `__all__` y el docstring de `main` faltantes, una coma final- y se
  corrigieron antes de aceptarlo, con el mismo criterio que se le aplica a
  cualquier instrumento propio.
  A diferencia de la ronda de SemVer, esta vez se le pidio explicitamente
  reconstruir a mano cada atajo declarado en `dont` antes de reportar exito:
  los tres quedaron bloqueados por el oraculo sin necesitar correccion.
- **`effective_go_checks` es la primera familia sobre prosa narrativa, no
  sobre un spec o checklist con items para enumerar.** Effective Go trae 15
  secciones y mas de 30 subsecciones de texto corrido, y decidir que cuenta
  como un nodo fue la primera decision de diseno, no la ultima: Poolside -la
  misma agente de SemVer y Rust API Guidelines- lo resolvio con una mezcla de
  los dos precedentes del repositorio, un nodo por titulo/subtitulo cuando
  alcanza y mas de uno cuando una subseccion trae varias tecnicas, como ya
  hacia `build_tailwind.py`.
  Su primera entrega cubria solo 10 de las 45 tecnicas identificables, sin
  avisar que era una muestra y no el documento completo -a diferencia de
  Tailwind o Stripe, que cubren exhaustivamente su seleccion curada-. Se le
  pidio expandir el grafo antes de aceptarlo; la segunda entrega llego a 45
  nodos con las 15 secciones representadas, verificado nodo por nodo.
  De esas 45, solo 3 son pila A (indentacion con tabs, cero parentesis en
  estructuras de control, llave de apertura en la misma linea). El resto trae
  un motivo de pila C nuevo para este repositorio: varias convenciones
  -indentacion, insercion de punto y coma, formato de columnas- ya las hace
  cumplir `gofmt`, el formateador oficial del lenguaje, asi que no hay nada
  que el codigo pueda violar de forma persistente sin que la propia
  herramienta lo corrija. Es una razon distinta a "no hay umbral" o
  "requiere juicio": es "la herramienta del lenguaje ya lo resuelve".
- **The Zen of Python es la unica fuente sin familia propia, y es lo
  correcto.** Sus 19 aforismos terminaron A=0/B=7/C=12: juicio estetico de
  diseno, no umbrales. La decision mas interesante fue negativa: se evaluo
  reusar `arch_checks.excepciones` para instrumentar "errors should never
  pass silently", y se descarto porque esa regla marca cualquier
  `except Exception` amplio -incluido uno que maneja el error de verdad, que
  el aforismo permite-, asi que reusarla habria sido un generador sistematico
  de falsos positivos, el mismo error que el precedente J1 ya nombra:
  tergiversar al autor para forzar una instrumentacion que no le corresponde.
  Sin pila A no hay `instruments/zen_checks.py`, no hay ejercicios, y los
  gates 2-4 no aplican a esta fuente: solo corre `okf_emit`/`validate_okf`.
- **The Agile Manifesto es la segunda fuente sin familia, y por un motivo
  distinto al Zen.** El Zen es juicio estetico sobre codigo; el Manifiesto
  Agil es juicio sobre como trabaja un equipo -colaboracion, ritmo,
  auto-organizacion-, ni siquiera del mismo tipo de artefacto que un
  instrumento pudiera leer. La decision mas interesante fue negativa otra
  vez: `git_checks.py --rule cadencia` ya mide algo parecido para Scrum y XP
  (fuente hermana, mismo tema), y se evaluo reusarla para "entrega temprana y
  continua" y "entregar software funcionando frecuentemente". Se descarto
  con tres razones documentadas en el `why_not`: sin `.git` en el checkout la
  regla da NO-VERIFICABLE, mide solo el hueco entre tags -no si lo entregado
  es realmente "software funcionando"-, y es un subconjunto parcial de una
  propiedad que en el fondo pide juicio de equipo. A=0/B=7/C=10, sin
  instrumento ni ejercicios, gates 2-4 no aplican.
  Antes de mergear se encontro y corrigio un defecto real: el script
  esperaba `agile-manifesto.txt` en la raiz del repositorio -el mismo lugar
  que usa `build_zen_of_python.py`, que declaro seguir como precedente
  explicito-, pero el archivo habia quedado escrito en `books/`. Se movio a
  la raiz para que coincidiera con su propio valor por defecto.

## Los ejercicios

Cada uno trae seed, solucion de referencia, oraculo congelado y spec. Hay cuatro
formas, y solo una deja el oraculo en rojo:

| Forma | Target | Oraculo sobre el seed |
|---|---|---|
| refactor | una funcion, una pagina, una plantilla, un archivo de despliegue | verde: no cambia el comportamiento |
| cambio de interfaz | una firma, una clase, un metodo | **rojo**: la tecnica cambia el nombre y el oraculo tiene que notarlo |
| nivel repo | el punto de entrada del proyecto | verde: la funcionalidad esta intacta |
| multi-modulo | el archivo que cruza una capa | verde: la estructura no cambia el resultado |

Los que agregan pruebas (cobertura, limites, anatomia) reparten distinto: **el
oraculo esta sellado y el `target` es OTRO archivo de pruebas**, el unico que se
puede tocar. Sin eso el contrato pediria editar lo que el mismo congela.

El de plantillas necesito una pieza mas: **el proyecto trae su motor**, un
mustache minimo de 40 lineas. El comportamiento observable de una plantilla es
lo que renderiza, y sin motor el oraculo no tendria nada que fijar. Es el mismo
reparto que en los de HTTP —el proyecto declara con que produce el artefacto— y
el motor es independiente de `template_checks` a proposito: si compartieran
codigo, un error de escapado los haria coincidir a los dos.

Ese ejercicio muestra el punto entero del reparto mejor que ninguno. Con datos
benignos, `{{{autor}}}` y `{{autor}}` renderizan **exactamente lo mismo**: la
diferencia aparece solo con contenido hostil, o sea justo con el caso que
ninguna prueba escrita con datos de ejemplo va a cubrir. El oraculo esta ciego
por construccion y el instrumento es lo unico que discrimina.

Los 26 de PEP 8 son los que mas usan la forma **cambio de interfaz**, que hasta
esta fuente casi no aparecia. Veintidos son refactorizaciones —sangria, espacios,
comas, comentarios— donde el oraculo esta ciego por definicion. Los otros cuatro
renombran algo que es API: una clase, una funcion, un metodo con su atributo, una
excepcion. Ahi el oraculo esta escrito contra el nombre de destino y **se pone en
rojo sobre el seed**, que es lo que esa forma existe para capturar: el nombre
viejo deja de existir y quien lo importaba deja de encontrarlo.

Uno de los 27 no admite la forma de ejercicio y esta declarado: `modulo` mide el
nombre del archivo, y el arreglo es renombrarlo. `touch_only` cubre el contenido
de un archivo, no su nombre — el mismo limite que ya tenian las cinco reglas de
git, encontrado esta vez en otra familia.

Los diez de accesibilidad son el caso donde **el oraculo tiene mas trabajo que
de costumbre**, y no porque mire mas: porque casi todos estos arreglos tienen un
atajo que pone el instrumento en verde sin arreglar nada. Borrar la animacion
deja `movimiento` contento, borrar el estilo deja a `contraste` sin nada que
medir, borrar la medida hace lo mismo con `toque`, y cambiar el texto visible
del boton "arregla" `etiquetaennombre` cambiando lo que la persona lee. Los
cinco atajos estan escritos en el `dont` de su spec **y frenados por el
oraculo**, comprobado uno por uno.

Dos de ellos muestran de paso una distincion del propio instrumento: borrar el
estilo no lo pone en rojo, lo pone en **exit 2**. Que no es verde, y ahi esta la
diferencia entre "no cumple" y "no puedo saber".

El de etiquetas es el mas fiel a lo que pasa en un repositorio real: el seed ya
muestra "Codigo de cupon", solo que en un `<span>` que no esta asociado a nada.
El arreglo no agrega una palabra a la pantalla — **para quien ve, antes y
despues son identicos**— y el lector de pantalla pasa de anunciar "cuadro de
edicion" a anunciar el campo. Es el ejemplo mas limpio de por que el oraculo no
alcanza.

Los ocho de entorno mueven el oraculo **fuera** de `proyecto/`, y no es un
detalle de organizacion: `entorno_checks` mide todos los `.py` del proyecto, asi
que un oraculo adentro seria medido como si fuera codigo de la app. En varias
reglas eso alcanza para cambiar el resultado — un `bind` en el oraculo pondria
`puerto` en verde sin que nadie ate un puerto.

Dos de ellos muestran hasta donde llega el oraculo. En el de config, la prueba
pone la clave en el entorno antes de importar y por eso pasa igual sobre el seed
y sobre la solucion: **dada la misma configuracion, el comportamiento es el
mismo**; lo que cambia es de donde sale la clave, y eso ningun test lo ve. En el
de daemonizar, el oraculo directamente **no llama a la ruta de arranque** — la
primera version si la llamaba y estaba mal de dos maneras: en POSIX habria
forkeado de verdad durante la prueba, y en Windows `os.fork` no existe y el
oraculo se ponia rojo sobre el seed. Lo detecto `test_exercises`, que compara el
oraculo contra el `kind` declarado. Que la ruta de arranque no se ejecute en
ninguna prueba es lo normal, y es exactamente por lo que hace falta un
instrumento que lea el codigo entero.

Los de HTTP necesitaron un paso mas, declarado en el spec como `preparar`: se
edita la app y se miden **las respuestas que produce**, asi que las capturas se
regeneran desde el target en cada corrida. No es un atajo: si el target fueran
las capturas, el ejercicio enseniaria a **falsificar la evidencia** en vez de
arreglar la causa. Es el mismo motivo por el que las tres reglas de git no
tienen ejercicio.

Para una pagina, el comportamiento observable es su contenido, y ahi el oraculo
tiene una obligacion extra: **no importa el instrumento**. Parsea con
`html.parser` por su cuenta aunque `html_checks` ya tenga un parser, porque un
oraculo que usa el parser del instrumento le da la razon por construccion — si
el parser se equivoca, los dos se equivocan igual y nadie lo nota.

Los 42 de la guia de Google son los que mas dependen del oraculo para no
confundir **cambio de redaccion** con **cambio de significado**. Arreglar
"Simply click the button" a "Click the button" cambia cada palabra del
enunciado salvo dos, y el oraculo tiene que quedar ciego a esa diferencia y
sensible solo al dato que importa: que sigue siendo el mismo boton. Por eso cada
oraculo afirma un hecho observable —una palabra clave, un dato, una estructura—
y no una cadena exacta; el mismo assert vale sobre el seed y sobre la solucion
por construccion, que es lo que la forma `refactor` exige. Seis de ellos traen
ademas el JSON con el vocabulario declarado —terminos, nombres de producto,
lenguaje inclusivo, jerga, tipos de aviso— que el instrumento exige por
`--lista`/`--productos`/`--inclusivo`/`--jerga`/`--avisos`.

Emitirlos junto con el resto del grafo destapo un defecto de forma: el
`signature` de uno de ellos era literalmente sintaxis de imagen Markdown
(`![Architecture diagram](diagram.png)`), y el emisor la escribe tal cual en el
contrato. `validate_okf` la leyo como un enlace real a un archivo que no existe.
Un `signature` describe la interfaz, no es markdown ejecutable — se reescribio
como texto plano.

Los diez de Tailwind son los primeros cuyo artefacto es **un proyecto entero**
y no un archivo suelto: solo UNO de sus archivos cambia entre el seed y la
solucion —el `vite.config.ts`, el `package.json`, la hoja de estilos— y el
resto queda fijo como contexto, igual que los ejercicios de `entorno_checks`.
El oraculo lee ese unico archivo y afirma lo que no depende de la tecnica: que
el `package.json` sigue declarando el mismo nombre y la misma version de
Tailwind, que el color del tema sigue siendo el mismo `oklch(...)`, que la
tarjeta sigue mostrando el mismo texto. Se comprobo que frena los atajos que su
`dont` prohibe: sacar `tailwindcss` del manifiesto en vez de sacar Sass, borrar
el contenido de un panel en vez de resolver el conflicto de utilidades, y
cambiar el valor del color en vez de solo su namespace — los tres ponen el
oraculo en rojo.

Los dos de Stripe son los mas chicos del repositorio, y cada uno mueve un solo
archivo de un proyecto de dos: sacar la clave literal de `config.py` sin tocar
`client.py`, y sacar el header de idempotencia de un `requests.get(...)` sin
cambiar de metodo. El oraculo afirma lo que no depende de la tecnica —que
`config.py` sigue exponiendo `STRIPE_KEY`, que `client.py` sigue siendo el
mismo GET a `customers`— y se comprobo que frena los dos atajos que su `dont`
prohibe: mover la clave a `client.py` en vez de resolverla en `config.py`, y
cambiar el GET por un POST en vez de sacar el header. Los dos ponen el oraculo
en rojo.

Los tres de SemVer, los tres de Rust API Guidelines y los tres de Effective
Go son los unicos que un
agente distinto escribio de punta a punta, y por eso su verificacion fue mas
estricta: para cada uno se reconstruyo el atajo declarado en `dont` a mano, en
vez de confiar en que el agente lo habia probado. Dos de los tres de SemVer
—`s09-prerelease`, `s10-build`— fallaron esa reconstruccion: el oraculo
original solo pedia que `__version__` siguiera siendo un string no vacio, y un
`1.0.0-alpha.1` reescrito como `1.0.0+alpha.1` (build metadata en vez de
pre-release) pasaba esa unica asercion igual de bien que la solucion real,
porque el instrumento tampoco objeta nada si el sufijo que mide no esta. Se
corrigio agregando una segunda asercion —que el string siga conteniendo `-`
(pre-release) o `+` (build) segun corresponda— y se reconfirmo que el atajo
ahora sí pone el oraculo en rojo sin tocar la asercion sobre el formato del
identificador, que es la tecnica que cada ejercicio mide.

Los tres de Rust API Guidelines pasaron la misma reconstruccion a mano sin
necesitar arreglo: borrar el `impl` entero de un getter, sacar `pub` de un
struct, o borrar el ejemplo rustdoc con `?` dejan el oraculo en rojo —cada uno
afirma que el artefacto observable (la firma publica, la visibilidad, el
ejemplo) sigue estando, sin juzgar la convencion que mide el instrumento—
porque a esta segunda ronda se le pidio explicitamente reconstruir cada atajo
antes de reportar exito, en vez de despues.

Los tres de Effective Go traen dos atajos por ejercicio en vez de uno: cambiar
el mensaje que imprime el programa (bloqueado por el oraculo) y revertir el
arreglo -tabs a espacios, parentesis de vuelta, llave a la linea de abajo-
(bloqueado por el instrumento). Los seis se reconstruyeron a mano y los seis
frenaron donde correspondia, sin necesitar arreglo.

## El repositorio contra sus propios instrumentos

Corriendo `checks` y `pep8_checks` sobre este mismo codigo aparecieron nueve
cosas, y la mitad eran defectos de los instrumentos y no del codigo:

| Que aparecio | Que era |
|---|---|
| `imports` marcaba `a11y_checks` | **regresion mia**: al agregar `ARTEFACTO` a las once familias parti el bloque de imports de una |
| `metodo` marcaba los diez `setUp` | **defecto del instrumento**: PEP 8 permite mixedCase donde ya es el estilo predominante. Se declara con `--impuesto` |
| `g4` marcaba `checks.py` | **defecto del instrumento**: leia lineas crudas, y la expresion regular que define los marcadores contiene los marcadores. Ahora lee comentarios y decoradores |
| `imports` marcaba las doce suites | **real**: `sys.path.insert` antes del import deja una sentencia en medio del bloque |
| `ambiguos`, `operador`, `g12` | **reales**: dos `l` de un caracter, nueve cortes despues del operador, una variable muerta |

Lo mas interesante fue una contradiccion entre dos instrumentos del propio
repositorio. Al arreglar `imports` con un modulo importado por su efecto, `g12`
lo marcaba como import sin usar; al declararlo con `# noqa`, **`g4` lo marcaba
como medida de seguridad cancelada**. Dos autores pidiendo cosas incompatibles
sobre el mismo archivo, que es lo mismo que pasa entre J1 y PEP 8 con los
imports con comodin. Se resolvio sin cancelar nada: el modulo expone una funcion
y las suites la usan, asi que el nombre se usa de verdad.

**Las 27 reglas de PEP 8, mas `g4` y `g12`, quedan en verde sobre todo el
repositorio**: los scripts, los once instrumentos y las catorce suites.

Cerrar las dos ultimas dejo una observacion que vale mas que el verde. `publica`
y `docstring` sobre el codigo de produccion pagan: 24 modulos que ahora declaran
que exponen, y 74 funciones publicas que ahora dicen que hacen — `main`, `build`,
`leer`, los metodos del arbol de HTML—. Sobre la suite de pruebas, en cambio,
167 de los 241 docstrings **repiten el nombre del metodo**: un
`test_g12_perdona_el_import_marcado_con_noqa` no gana nada con un docstring que
diga lo mismo. Los 70 que ya existian ahi son justo los que explican una
sutileza que el nombre no alcanza a decir.

O sea: la regla es una lectura correcta de PEP 8 y su valor **depende del
alcance**. En codigo que otro importa, un docstring es la interfaz. En una suite
bien nombrada, es una repeticion. Queda anotado porque es el mismo patron que el
grafo encontro en WCAG y en la clausula del sufijo `Error`: un criterio correcto
puede pedir algo que en cierto contexto no aporta, y la unica salida honesta es
decirlo con el numero al lado.

## Que falta, y por que

`tests/test_cobertura.py` mantiene este inventario exacto: falla si aparece un
instrumento sin ejercicio que nadie declaro, y tambien si sobra una excepcion que
ya no hace falta.

| Que | n | Por que |
|---|---|---|
| tecnicas `proxy` | 17 | leen un tablero o un calendario, artefactos que este repositorio no tiene |
| `pep8_checks --rule modulo` sin ejercicio | 1 regla | el arreglo es **renombrar el archivo**, y `touch_only` cubre el contenido de un archivo y no su nombre. Es el mismo limite que las de git, encontrado en otra familia |
| `git_checks` sin ejercicio | 5 reglas | el arreglo es integrar una rama, marcar una entrega o poner el proyecto bajo control de versiones: `touch_only` cubre archivos, no commits |
| Scrum y XP sin script | 5 | 88 necesita el historial del proveedor de CI, o sea red, que el proyecto prohibe; 118-121 son el mismo `test_command` con etiqueta distinta y envolverlos duplicaria `e2` |
| J1 | 1 | su consejo es *usar imports con comodin*, que en Python el estilo prohibe. Implementarla invirtiendo el consejo seria tergiversar al autor |

**Ninguna fila es un instrumento que falte ni un ejercicio pendiente.** Las 206
tecnicas de pila A tienen instrumento, y toda regla que admite la forma de
ejercicio lo tiene. El resto son limites, no deudas: un artefacto que este
repositorio no tiene, una forma de contrato que no aplica, una prohibicion del
proyecto y un consejo que en Python no se puede seguir sin tergiversar al
autor.

La tentacion con las de git seria darle al
ejercicio un script que fabrique el historial y poner **ese** script como target:
seria enseñar a fabricar un historial que se vea bien, o sea lo contrario de la
tecnica.

## Lo que evita que esto se pudra

Veinte suites, 304 pruebas, y cada suite existe por un error concreto que ya paso.

| Suite | Que sostiene |
|---|---|
| `test_checks` · `test_repo_checks` · `test_arch_checks` · `test_git_checks` · `test_mutation_checks` · `test_html_checks` · `test_http_checks` · `test_template_checks` · `test_entorno_checks` · `test_a11y_checks` · `test_pep8_checks` · `test_prosa_checks` · `test_tailwind_checks` · `test_stripe_checks` · `test_semver_checks` · `test_rust_api_checks` · `test_effective_go_checks` | cada instrumento contra un caso rojo y uno verde. **Un instrumento que nunca dispara pasa todos los gates y no mide nada** |
| `test_exercises` | coherencia de los 151 ejercicios: instrumento verde sobre la solucion, rojo sobre el seed, y oraculo acorde al `kind` declarado |
| `test_memoria` | exportar, consultar y fusionar; comprueba contra el disco que la memoria exporte TODAS las familias y que cada una declare sobre que mide. Las dos existen por el mismo defecto repetido: una lista escrita a mano que queda vieja y deja el bundle incompleto sin que nada falle; incluye el contraste que justifica la identidad estable: con ids con prosa las dos ediciones no se fusionan y el desacuerdo pasa desapercibido |
| `test_cobertura` | dos invariantes: que ningun id de nodo lleve prosa del titulo, y que toda tecnica con instrumento tenga ejercicio salvo excepciones declaradas con su motivo |

Los errores que las hicieron nacer:

- **`check_g29` quedo escrito y sin registrar**, midiendo nada. Comparar los
  casos de prueba contra el registro no lo detectaba: si la regla falta en los
  dos lados, los conjuntos coinciden. Ahora se comparan las funciones del modulo.
- **En G29 declare `kind: refactor` con un seed que cambiaba el comportamiento**
  (`cupos != 0` contra `cupos > 0`, distinto para negativos). El contrato decia
  "el comportamiento no cambia" y era falso.
- **`check_g9` marcaba como muerta a toda API publica bien escrita**, porque una
  funcion publica no se llama dentro de su propio archivo. Ahora exige `__all__`
  y sin el sale con **exit 2**: "no puedo saber" no es "esta limpio".
- **`check_aislamiento` aislaba de a modulo y no detectaba nada**: una prueba que
  depende de su vecina pasa igual cuando el modulo corre entero. Ahora corre cada
  prueba por separado.
- **Los dos emisores tenian el mismo bug de indice**: un bloque compartido, asi
  que emitir un segundo libro dejaba huerfanos los nodos del primero. Comprobado
  antes de arreglarlo: 67 ORPHAN.
- **Un test que decia cubrir los elementos vacios de HTML no tenia dientes.**
  Miraba si un `<button>` conservaba su ancestro, y como `handle_endtag`
  recupera subiendo hasta el tag que cierra, sacar el manejo de void elements
  cambia la forma del arbol pero no la alcanzabilidad de los ancestros. Ahora
  comprueba lo que la guarda de verdad garantiza: que un `<img>` no se quede con
  sus hermanos como hijos.
- **Los ids de nodo dependian del idioma del libro**, y eso hacia la memoria no
  fusionable. Es el defecto que menos se veia de todos: cada grafo validaba
  perfecto por separado, y el problema solo aparecia al intentar juntar dos.

## Garantias de los emisores

Los dos abortan con exit 1 **antes de escribir nada**. Un grafo a medias es peor
que ninguno.

`okf_emit.py` aborta si un enlace apunta a un id inexistente, si un nodo de pila
A no declara `instrument` o `verification`, si un tag tiene mayusculas, si el
`type` no esta en el vocabulario OKF o si hay ids duplicados. La emision es
idempotente: dos corridas producen los mismos bytes.

`contract_emit.py` aborta si el `budget` usa una subclave que el gate no lee, si
el nodo OKF referenciado no existe, si faltan campos requeridos, si hay menos de
dos `examples` o ningun `stop_if`.

**La regla de pila A no es cosmetica**: impide el unico error que este pipeline
existe para no cometer, que es declarar contractable algo sin instrumento que lo
mida.

El sello `tests_sha256` se calcula con newlines normalizados a LF, igual que el
validador. Verificado: agregar un comentario al oraculo dispara
`FM_TESTS_FROZEN` con hash esperado y hash actual.

### Por que el grafo primero

El paso que decide si esto sirve no es generar nodos: es **cablearlos**.
`validate_okf.py` rechaza con `ORPHAN` cualquier nodo no alcanzable desde
`index.md`. Prueba de que el cableado es lo que hace el trabajo: si se borra el
enlace de `index.md` a la carpeta del libro, el validador pasa de 0 errores a
**67 ORPHAN** sobre los mismos archivos.

## Que se toma del libro y que no

El grafo **no reproduce el texto de los autores**. Cada nodo lleva el nombre de
la tecnica y su ubicacion (`capitulo 17, F1`), para que quien tenga el libro
pueda ir a leerla, y nada mas.

Eso no le cuesta nada al pipeline, y la razon es el hallazgo central: **la
propiedad medible vive en el instrumento, no en la prosa que la describe**. El
grafo llego a tener 66 citas de Codigo Limpio; sacarlas dejo los contratos y los
gates exactamente igual de verdes.

El campo `quote` sigue existiendo en el emisor por si el libro de origen lo
permite. Estos grafos simplemente no lo llenan.

## Licencia

MIT, ver [LICENSE](LICENSE).

Cubre el codigo de este repositorio: los emisores, los instrumentos, las pruebas
y los ejercicios. **No cubre los libros de los que sale el grafo.** Los nombres
de las tecnicas son de sus autores; este repositorio los referencia para poder
apuntar a donde vive cada una, y no reproduce su texto.
