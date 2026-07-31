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

Cinco fuentes, 327 nodos, 44 contratos ejecutables, 45 instrumentos en ocho
familias. Los cuatro gates en verde: `validate_okf`, `validate_contracts`,
`validate_test_commands` y las 107 pruebas propias.

| Fuente | items | contractable | `instrumented` | con script | ejercicios |
|---|---|---|---|---|---|
| The Twelve-Factor App (A. Wiggins) | 16 | 62,5% | **62,5%** | 0 | 0 |
| Codigo Limpio (R. C. Martin) | 66 | 48,5% | **48,5%** | 31 | 28 |
| Arquitectura Java solida (C. Alvarez Caules) | 33 | 45,5% | **45,5%** | 15 | 6 |
| Scrum y eXtreme Programming (E. Bahit) | 153 | 25,5% | **14,4%** | 17 | 4 |
| htmx ~ Documentation | 59 | 10,2% | **10,2%** | 6 | 6 |
| **Total** | **327** | **102** | **85** | **69** | **44** |

Dos de las cinco no son libros, y estan para probar hasta donde llega el metodo.
La documentacion de htmx cae al 10,2% por una razon distinta a la de Scrum —no
habla de personas, habla de codigo— pero **describir una API no es prescribir
una tecnica**, y por eso casi la mitad cae en pila C por definicion del genero.

Los doce factores van al otro extremo por el motivo simetrico: **un manifiesto
es prescripcion pura**, sin una linea de relleno, y da el porcentaje mas alto de
las cinco. Se sumo con una prediccion hecha antes de triajar y escrita en el
script de build: si la contractabilidad la decide que el autor haya
operacionalizado la tecnica, un documento asi tiene que quedar por encima de los
libros de codigo. Quedo. Sobre los doce factores solos, sin el preambulo, es
**10 de 12**.

Su corpus es el mas chico —16 titulos— y no por muestreo: cada factor es una
pagina con titulo, bajada y sin subsecciones, comprobado pagina por pagina. Con
n=16 cada item vale 6,3 puntos, asi que el porcentaje es real pero la precision
implicita no.

Ademas: 17 tecnicas `proxy`, 97 en pila B (tecnica real sin propiedad medible)
y 128 en pila C (conocimiento). 23 enlaces cruzan de una fuente a otra.

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

## Los hallazgos

### 1. La distribucion es bimodal, no un gradiente

Siete fuentes medidas (las cinco del grafo, mas Proyectos Agiles con Scrum y
Habitos Atomicos) dan 62,5%, 48%, 45%, 14%, 10%, 3,4% y 0% de `instrumented`.
Pero el 14,4% de Scrum y XP **no es un valor intermedio**: es el promedio
ponderado de dos poblaciones.

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

La quinta fuente agrego un modo arriba, en 62,5%, y con eso el eje se lee mejor:
lo que ordena la distribucion **no es el dominio sino el genero**. Un manifiesto
(prescripcion pura) queda arriba de un libro de codigo (prescripcion mas
explicacion), que queda arriba de un libro de proceso (prescripcion mas
personas), que queda arriba de documentacion de referencia (descripcion de una
API). El dominio de los doce factores es infraestructura, tan lejos del AST como
Scrum, y sin embargo es el mas contractable de los cinco.

### 2. La contractabilidad la decide si el autor operacionalizo la tecnica

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

### 4. Los principios de arquitectura son tan medibles como las heuristicas de codigo

Prediccion razonable para Arquitectura Java: mismo artefacto que Codigo Limpio
pero tecnicas mas semanticas, o sea resultado intermedio. Salio 45,5%, casi
igual. La razon no es obvia: **son propiedades del grafo de dependencias e
instanciacion**, que es lo que el analisis estatico lee de forma nativa.
"Semantico" para un humano no implica "no medible" para un parser.

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

Lo tienen **188 de las 327**, y el reparto no es casual:

| Pila | Con alias | Regla |
|---|---|---|
| A (medibles) | **102 de 102** | exigido por prueba: son las que tienen instrumento y contrato, o sea las que un agente va a buscar |
| B (no medibles) | 83 de 97 | se completan las que tienen nombre reconocido |
| C (conocimiento) | 3 de 128 | no aplica: son temas, tecnologias y pasos de tutorial |

Las 14 de pila B que quedan afuera son subsecciones sin nombre propio: nueve de
Scrum y XP —tres titulos repetidos "Funciones y responsabilidades", dos
sub-pasos del Planning Poker, dos secciones de "cuando y como"— y cinco de htmx
que nombran una combinacion de atributos y no una tecnica ("Configure a Request
With Events"). **Inventarles un nombre canonico seria meter ruido en la
busqueda**, que es lo contrario de lo que el alias existe para hacer.

El alias es el handle que cruza idiomas **y libros**: `buscar DRY` devuelve las
cinco entradas de los tres libros de codigo, todas apuntando al mismo instrumento.

## La memoria portable

`memoria.py` exporta todo lo extraido a **un solo archivo** y lo hace
consultable. Es lo que otro agente necesita para usar este conocimiento **sin
tener los libros**.

```bash
python memoria.py exportar          # -> memoria.json: 327 tecnicas, 46 instrumentos
python memoria.py buscar DRY        # la misma tecnica en los tres libros
python memoria.py medibles          # las que tienen instrumento, con su comando
python memoria.py aplicar codigo.py # que de todo lo que se aplica a este codigo
python memoria.py fusionar a.json b.json -o c.json
```

El bundle son **305 KB**: `memoria.json` + `memoria.py` + `instruments/`.
Verificado: copiado a un directorio limpio, sin `books/`, sin `exercises/`, sin
PDF y sin el repo, `aplicar` corre **26 instrumentos** sobre un archivo
cualquiera y reporta los que estan en rojo con la tecnica que senala cada uno
—sobre una funcion de ejemplo, 6: cadena de Demeter, variable lejos de su uso,
import sin usar, numeros magicos, expresion de limite repetida y exceso de
parametros—.

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
2 memoria(s), 393 entradas -> 327 tecnicas (66 fusionadas) en fusionada.json

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
| ids estables (`g36`) | 327 + 66 | **327 tecnicas** | **2 reportados** |
| ids con slug (`g36-evitar-...`) | 327 + 66 | 393 tecnicas | 0 |

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
python okf_emit.py books/codigo-limpio.json --out out/knowledge
python contract_emit.py exercises --out out --book codigo-limpio

python <KDD>/scripts/validate_okf.py out/knowledge
python <KDD>/scripts/validate_contracts.py out/knowledge/contracts --repo-root out
python <KDD>/scripts/validate_test_commands.py out/knowledge/contracts out
```

`out/` no se versiona: se regenera entero desde `books/` y `exercises/`, sin
necesidad del PDF.

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

45 reglas en ocho familias. Que varias tecnicas compartan una no es un atajo: es
que preguntan lo mismo.

| Familia | Reglas | Mide sobre | Ejemplo |
|---|---|---|---|
| `checks.py` | 22 | el AST de un archivo Python | duplicacion, numeros magicos, ley de Demeter |
| `repo_checks.py` | 7 | el proyecto entero | un comando para probar, cobertura, tiempo de suite |
| `arch_checks.py` | 6 | relaciones entre modulos | capas, instanciacion, ISP |
| `git_checks.py` | 3 | el historial | cadencia de entregas, ramas sin integrar |
| `html_checks.py` | 3 | el DOM | mejora progresiva, token CSRF, indicador de request |
| `http_checks.py` | 2 | respuestas capturadas | `Vary: HX-Request`, politica de seguridad |
| `template_checks.py` | 1 | plantillas sin renderizar | interpolacion sin escapar |
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
- **`mutation_checks` escribe sobre el archivo que mide**, asi que tiene dos
  obligaciones extra con test propio: restaurarlo siempre, y salir con exit 2 si
  la suite ya venia en rojo — con la suite rota no se puede saber si mata
  mutantes o si falla sola.

## Los ejercicios

Cada uno trae seed, solucion de referencia, oraculo congelado y spec. Hay cuatro
formas, y solo una deja el oraculo en rojo:

| Forma | Target | Oraculo sobre el seed |
|---|---|---|
| refactor | una funcion o una pagina | verde: no cambia el comportamiento |
| cambio de interfaz | una firma | **rojo**: la tecnica cambia la firma |
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

## Que falta, y por que

`tests/test_cobertura.py` mantiene este inventario exacto: falla si aparece un
instrumento sin ejercicio que nadie declaro, y tambien si sobra una excepcion que
ya no hace falta.

| Que | n | Por que |
|---|---|---|
| doce factores sin instrumento | 10 | la fuente entro recien; sus tecnicas leen el manifiesto de dependencias, el historial de releases y los archivos de despliegue, y esos instrumentos todavia no estan escritos. Es lo unico de esta lista que se arregla trabajando |
| tecnicas `proxy` | 17 | leen un tablero o un calendario, artefactos que este repositorio no tiene |
| `git_checks` sin ejercicio | 3 reglas | el arreglo es integrar una rama o marcar una entrega: `touch_only` cubre archivos, no commits |
| Scrum y XP sin script | 5 | 88 necesita el historial del proveedor de CI, o sea red, que el proyecto prohibe; 118-121 son el mismo `test_command` con etiqueta distinta y envolverlos duplicaria `e2` |
| J1 | 1 | su consejo es *usar imports con comodin*, que en Python el estilo prohibe. Implementarla invirtiendo el consejo seria tergiversar al autor |

**Solo la primera es un instrumento que falte.** Las seis tecnicas
medibles de htmx —las tres de HTML, las dos de HTTP y la de plantillas— tienen
instrumento y ejercicio; las diez de los doce factores estan declaradas y sin
escribir. Las otras tres filas son limites, no deudas: un artefacto que este
repositorio no tiene, una forma de contrato que no aplica, una prohibicion del
proyecto y un consejo que en Python no se puede seguir sin tergiversar al
autor.

Ninguna razon es "no se puede medir". La tentacion con las de git seria darle al
ejercicio un script que fabrique el historial y poner **ese** script como target:
seria enseñar a fabricar un historial que se vea bien, o sea lo contrario de la
tecnica.

## Lo que evita que esto se pudra

Once suites, 107 pruebas, y cada suite existe por un error concreto que ya paso.

| Suite | Que sostiene |
|---|---|
| `test_checks` · `test_repo_checks` · `test_arch_checks` · `test_git_checks` · `test_mutation_checks` · `test_html_checks` · `test_http_checks` · `test_template_checks` | cada instrumento contra un caso rojo y uno verde. **Un instrumento que nunca dispara pasa todos los gates y no mide nada** |
| `test_exercises` | coherencia de los 44 ejercicios: instrumento verde sobre la solucion, rojo sobre el seed, y oraculo acorde al `kind` declarado |
| `test_memoria` | exportar, consultar y fusionar; incluye el contraste que justifica la identidad estable: con ids con prosa las dos ediciones no se fusionan y el desacuerdo pasa desapercibido |
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
