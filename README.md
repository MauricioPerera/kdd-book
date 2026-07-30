# kdd-book

Pipeline que deconstruye un libro en un grafo OKF de conocimiento y, donde hay
instrumento, en contratos hibridos verificables de KDD.

Estado: **fase 1 (grafo OKF) y fase 2 (contratos) funcionando**, verificadas
contra los validadores reales del repo KDD.

```
build -> okf_emit -> contract_emit -> validate_okf | validate_contracts | validate_test_commands
                                          exit 0          exit 0                exit 0
```

## Fase 2: los contratos

Dos restricciones del validador definen el diseno, y ninguna es obvia hasta que
se lee el codigo:

**1. `budget` solo admite cuatro subclaves**: `cyclomatic_max`, `nesting_max`,
`lines_max`, `params_max`. Son las que lee el gate de nivel 2; cualquier otra es
un error porque *el tope quedaria ignorado en silencio*. De las 32 heuristicas
contractables de Codigo Limpio **una sola (F1) mapea directo**. Las demas no
pueden apoyarse en el budget: necesitan un instrumento propio.

**2. `test_command` corre con `shlex.split` sin shell**, asi que no admite `&&`.
Tiene que ser un comando unico.

De esas dos sale `instruments/gate.py`, que resulta ser el diseno correcto:

| Corre | Verifica | Si falla |
|---|---|---|
| oraculo congelado | no rompiste el comportamiento | `ORACULO ROJO` |
| instrumento | aplicaste la tecnica | `INSTRUMENTO ROJO` |

Los dos hacen falta y hay que saber cual fallo. Una refactorizacion, por
definicion, no cambia el comportamiento observable: **el oraculo pasa igual
antes y despues**, asi que ningun test puede verificarla. Y al reves, un
instrumento verde sobre codigo roto no vale nada.

Las tres formas que puede tomar un ejercicio:

- **G36 (Ley de Demeter)** - refactor puro. El oraculo esta verde sobre el seed
  y sobre la solucion; lo unico que discrimina es `chain_depth.py`. Verificado:
  con el seed el gate reporta *"el oraculo esta verde: no rompiste nada, pero no
  aplicaste la tecnica"*.
- **F1 (demasiados argumentos)** - cambia la interfaz, asi que el oraculo
  arranca en rojo. El instrumento sigue haciendo falta: sin el, nada impide
  satisfacer el oraculo con cuatro parametros.
- **E2, capas, aislamiento** - nivel repo o multi-modulo: el `target` no es una
  funcion sino el punto de entrada del proyecto o el archivo que cruza una capa.
  El oraculo prueba la funcionalidad y queda ciego a la propiedad estructural.

### Instrumentos

**60 de las 69 tecnicas `instrumented` del grafo tienen script**, repartidas en
cuatro familias: `checks.py` (AST de un archivo), `repo_checks.py` (propiedades
del proyecto), `git_checks.py` (propiedades del historial) y `arch_checks.py`
(relaciones entre modulos). En Codigo Limpio, No son 28 scripts:
son `instruments/checks.py`, un registro de 18 checks que comparten el andamiaje
AST (mas dos alias, porque el libro define G15 igual que F3 y F4 igual que G9), y
dos instrumentos dedicados para F1 y G36. Agregar una medicion cuesta una funcion
corta y una entrada en `RULES`.

```bash
python instruments/checks.py --list
python instruments/checks.py --rule g23 --max 2 target.py
```

Cada check tiene en `tests/test_checks.py` un caso rojo y uno verde: que detecte
lo que dice detectar, y que no grite sobre codigo conforme. **Un instrumento que
nunca dispara pasa todos los gates y no mide nada**, que es el fallo silencioso
que este pipeline existe para evitar.

Hay ademas un test estructural que compara las funciones `check_*` del modulo
contra `RULES`. Existe porque el agujero aparecio de verdad: `check_g29` quedo
escrito y sin registrar, y comparar los casos de prueba contra `RULES` no lo
detecta — si la regla falta en los dos lados, los conjuntos coinciden igual.

### Contratos de nivel repo

E1, E2, G24, T1, T2 y T9 no hablan de un archivo sino del proyecto, asi que el
`target` deja de ser codigo a refactorizar y pasa a ser el **punto de entrada**.
La division se mantiene y se vuelve mas clara:

- **oraculo**: los tests del proyecto siguen pasando, o sea la funcionalidad esta intacta
- **instrumento**: la propiedad del repo — un comando, cobertura, tiempo, convenciones

`instruments/repo_checks.py`, todo con stdlib: `subprocess` para ejecutar los
comandos y `trace` para cobertura, sin dependencias externas. Usa `subprocess`
por la misma razon por la que `validate_test_commands.py` del repo KDD rompe su
propia convencion `forbids: subprocess`: **para medir si algo corre, hay que
correrlo**.

Dos decisiones que conviene tener explicitas:

- **G24** verifica un subconjunto declarado (largo de linea, tabuladores,
  espacios al final, salto final), no un linter completo. Decir "convenciones
  estandar" sin enumerarlas seria pedir algo no verificable.
- **E2** no se conforma con que el comando salga 0: exige que reporte cuantas
  pruebas corrio. Un `test` que no prueba nada tambien sale 0, y ese es
  justamente el fallo silencioso que la heuristica quiere evitar.

### Las 4 que faltan, y por que

| Heuristicas | Por que no estan |
|---|---|
| J1, J2 | son construcciones de Java (imports comodin, interfaz de constantes) y los ejercicios son Python |
| G3, T5 | condiciones de limite: se verifican con mutantes, o sea un motor de mutacion |

Ninguna razon es "no se puede medir": son formas de contrato que este pipeline
todavia no emite.

### Ejercicios

**36 contratos ejecutables** sobre los tres libros. Cada ejercicio trae seed,
solucion de referencia, oraculo congelado y spec. Lo que los mantiene sanos es
`tests/test_exercises.py`, que verifica los cuatro criterios en todos a la vez:

1. el instrumento esta verde sobre la solucion;
2. el instrumento esta rojo sobre el seed (si no, el ejercicio ya viene hecho);
3. el oraculo pasa sobre la solucion;
4. el oraculo se comporta como manda el `kind` declarado.

Existe por un error concreto: en G29 declare `kind: refactor` y escribi un seed
que cambiaba el comportamiento (`cupos != 0` contra `cupos > 0`, distinto para
negativos). El contrato decia "el comportamiento no cambia" y era falso. Despues
encontro un defecto peor, y del instrumento y no del ejercicio: `check_g9`
marcaba como muerta a cualquier funcion no referenciada dentro de su propio
archivo, o sea a toda API publica bien escrita.

Los cinco contratos de nivel repo traen cada uno un proyecto de ejemplo. El
oraculo prueba la funcionalidad y queda ciego a la propiedad del repositorio;
el instrumento mide la propiedad. En T1 el reparto es explicito: el oraculo
`test_cupos.py` esta sellado y cubre dos de los cinco caminos a proposito, y el
`target` es **otro** archivo de pruebas, el unico que se puede tocar.

### Garantias de `contract_emit.py`

Aborta con exit 1 antes de escribir si el `budget` usa una subclave que el gate
no lee, si el nodo OKF referenciado no existe (el enlace quedaria roto y
`validate_okf.py` lo rechazaria), si faltan campos requeridos, si hay menos de
dos `examples` o ningun `stop_if`.

El sello `tests_sha256` se calcula con newlines normalizados a LF, igual que
`_calculate_tests_hash` del validador. Verificado: agregar un comentario al
oraculo dispara `FM_TESTS_FROZEN` con hash esperado y hash actual.

## Por que el grafo primero

El paso que decide si esto sirve no es generar nodos: es **cablearlos**.
`validate_okf.py` del repo KDD rechaza con `ORPHAN` cualquier nodo que no sea
alcanzable desde `index.md`, y con `LINK` cualquier enlace que no resuelva. Un
generador que emite archivos sueltos produce un grafo invalido, aunque cada
archivo por separado se vea bien.

Prueba de que el cableado es lo que hace el trabajo: si se borra el enlace de
`index.md` a la carpeta del libro, el validador pasa de 0 errores a **67
ORPHAN** sobre los mismos archivos.

## Tres libros en un grafo

| Libro | nodos | contractable | instrumented |
|---|---|---|---|
| Codigo Limpio | 67 | 48% | 48% |
| Arquitectura Java solida | 34 | 45,5% | 45,5% |
| Scrum y eXtreme Programming | 154 | 25,5% | 14,4% |

Arquitectura Java tiene **corpus mas debil que los otros dos** y conviene
saberlo antes de leer su numero: es un tutorial progresivo, no tiene lista
cerrada de conclusiones del autor, y sus 33 items salieron de titulos de
capitulo identificados por el triaje. n es menor y las barras de error mas
anchas. Aun asi el resultado es claro: sus 15 tecnicas contractables son las 15
`instrumented`, porque los principios de arquitectura son propiedades del grafo
de imports y de instanciacion, que es lo que el analisis estatico lee de forma
nativa. "Semantico" para un humano no implica "no medible" para un parser.

El 14,4% del segundo **no es un valor intermedio**: es el promedio ponderado de
dos poblaciones. Medido por seccion:

| Seccion | instrumented |
|---|---|
| Refactoring | 55% |
| TDD | 40% |
| Integracion continua | 29% |
| Programacion extrema y Coding Dojo | 13% |
| Introduccion y agilismo | 3% |
| Scrum | 0% |
| Combinar Scrum y XP | 0% |
| Kanban | 0% |

Ninguna seccion cae en el medio. Por eso **el ruteo se decide por seccion, no
por libro**: un numero a nivel libro mandaria todo a "solo grafo OKF" y tiraria
el capitulo de Refactoring, que da contratos tan buenos como los de Codigo
Limpio.

### El enlace que justifica que esto sea un grafo

`scrum-xp/142-expresiones-extensas` enlaza a
`codigo-limpio/g19-usar-variables-explicativas`. **Son la misma refactorizacion
y quedan en pilas distintas.**

Martin la deja fuera de lo contractable: dice que conviene siempre mas y que es
dificil excederse — o sea sin umbral — y ademas le exige nombres descriptivos,
que es la mitad no medible. Bahit la deja contractable, y de un modo casi
provocador: su ejemplo extrae las subexpresiones a variables llamadas `$a`,
`$b`, `$c`, `$d`. Al no reclamar nada del nombre, lo unico que queda de la
tecnica es la reduccion de complejidad de la expresion, que es lo que un parser
cuenta.

**La contractabilidad no la decide la tecnica ni el dominio: la decide si el
autor la operacionalizo.** Eso solo se puede afirmar con los dos nodos a la
vista, y por eso el grafo tiene enlaces entre libros y no es una tabla por
libro.

El tercer libro trae el mismo caso otra vez, y en el sentido contrario.
`arquitectura-java/08-el-principio-srp` enlaza a
`codigo-limpio/g30-las-funciones-solo-deben-hacer-una-cosa`: **mismo principio,
pilas distintas**. Martin nunca lo aterriza — cuenta operaciones semanticas y no
da un numero — asi que su nodo queda en pila B. Caules lo aplica como separacion
de capas, la JSP no contiene codigo de persistencia, y eso es una regla de
imports. Que el caso aparezca dos veces con los papeles cambiados es lo que lo
vuelve un patron y no una anecdota.

`arquitectura-java/04-el-principio-dry` es la primera tecnica que aparece en los
**tres** libros, y los tres autores la operacionalizan: los tres nodos son
contractables y comparten instrumento.

De las 39 tecnicas contractables del segundo libro:

| | n | |
|---|---|---|
| `instrumented` con script corriendo | 17 | |
| `instrumented` sin script | 5 | 88 necesita el historial del proveedor de CI, o sea red, y el proyecto la prohibe; 118-121 son el mismo `test_command` con etiqueta distinta y envolverlos duplicaria e2 |
| `proxy` | 17 | leen un tablero o un calendario, artefactos que este repositorio no tiene |

Cuatro instrumentos se reusan entre libros sin tocar una linea:
`checks.py --rule g5` para las tres formas de duplicacion que enumera Bahit,
`checks.py --rule g12` para sus variables temporales mal usadas, y
`repo_checks.py --rule g24` y `--rule e2` para codigo estandar y para testing.

### Instrumentos de arquitectura

`instruments/arch_checks.py` es familia propia porque estas mediciones necesitan
que el proyecto **declare** algo: cuales son sus capas, que capa puede llamar a
cual, cual es el esquema de la tabla. Y es correcto que sea explicito: una regla
de capas que el instrumento adivine no es una regla, es una opinion. Sin la
declaracion salen con exit 2, no con verde.

Seis reglas que cubren doce tecnicas, porque varias son la misma propiedad vista
desde distintas alturas:

| Regla | Cubre |
|---|---|
| `capas` | SRP, MVC, MVC 2, DAO, capa de servicio |
| `instanciacion` | inversion de control, Factory, inyeccion de dependencia |
| `excepciones` · `isp` · `aop` · `coc` | una cada una |

Que cinco tecnicas compartan instrumento no es un atajo: las cinco preguntan lo
mismo, quien puede depender de quien.

### Instrumentos que leen git

Tres heuristicas hablan de propiedades que no viven en un archivo ni en el
tablero sino en el historial: cada cuanto se entrega, si el codigo esta
integrado en un solo lugar, y si el test se escribio antes que la
implementacion. Estan en `instruments/git_checks.py` y **siguen siendo
`instrumented`, no `proxy`: git no lo llena nadie a mano.** Las fechas de
commits y tags las pone la herramienta. Es la diferencia con el tablero, que
tiene timestamps automaticos pero contenido escrito por personas.

El caso del ciclo TDD merece decirse con cuidado. "Escribir el test y hacer que
falle" es una propiedad del **proceso**, y el estado final del codigo no la
conserva. El historial si: si el archivo de pruebas entro en un commit anterior
al de la implementacion, el orden se cumplio. Es lo unico verificable despues
de los hechos, y no hay que confundirlo con haber visto el test en rojo.

## Licencia

MIT, ver [LICENSE](LICENSE).

Cubre el codigo de este repositorio: los emisores, los instrumentos, las
pruebas y los ejercicios. **No cubre el libro del que sale el grafo.** Los
nombres de las heuristicas son de su autor; este repositorio los referencia
para poder apuntar a donde esta cada tecnica, y no reproduce su texto.

## Que se toma del libro y que no

El grafo **no reproduce el texto del autor**. Cada nodo lleva el nombre de la
heuristica y su ubicacion (`capitulo 17, F1`), para que quien tenga el libro
pueda ir a leerla, y nada mas.

Eso no le cuesta nada al pipeline, y la razon es el hallazgo central del
proyecto: **la propiedad medible vive en el instrumento, no en la prosa que la
describe**. La cita explica por que F1 importa; quien decide si F1 se cumple es
`params_max: 3`. Sacar las 66 citas dejo los 26 contratos y los cuatro gates
exactamente igual de verdes.

El campo `quote` sigue existiendo en el emisor por si el libro de origen lo
permite. Este grafo simplemente no lo llena.

## Piezas

| Pieza | Que hace | Determinista |
|---|---|---|
| extraccion | PDF -> texto UTF-8 (PyMuPDF) | si |
| `build_<libro>.py` | texto -> `books/<libro>.json`: titulos y citas del libro + el triaje declarado | si, dado el triaje |
| triaje | clasificar cada tecnica en pila A/B/C | no: es juicio, y va explicito en el build |
| `okf_emit.py` | JSON -> arbol `knowledge/` que pasa `validate_okf.py` | si |

El triaje es la unica pieza con juicio, y esta aislada a proposito: vive como
tabla legible en el script de build, auditable linea por linea.

## Uso

```bash
python build_codigo_limpio.py <texto-extraido.txt>
python okf_emit.py books/codigo-limpio.json --out out/knowledge
python <KDD>/scripts/validate_okf.py out/knowledge   # exit 0
```

## Garantias de `okf_emit.py`

Aborta con exit 1 **sin escribir nada** si:

- un `links` apunta a un id inexistente (seria `LINK` en el validador);
- un nodo de pila A no declara `instrument` o `verification`;
- un tag tiene mayusculas, un `type` no esta en el vocabulario OKF, hay ids
  duplicados o falta un campo requerido.

Un grafo a medias es peor que ninguno, asi que la validacion completa ocurre
antes de tocar el disco. La emision es idempotente: correrla dos veces produce
los mismos bytes.

La regla de la pila A no es cosmetica. Es la que impide el unico error que este
pipeline existe para no cometer: **declarar contractable algo que no tiene
instrumento que lo mida**, que es prometer verificacion que no existe.

## Piso de la fase 1

El grafo actual conecta los nodos entre si solo donde el libro establece la
relacion. Enlazar por vecindad tematica inflaria el grafo sin agregar
informacion. Los enlaces valiosos que faltan son los que cruzan libros: la
misma tecnica operacionalizada por un autor y no por otro.

## Medicion

La fraccion que decide el ruteo de un libro es `instrumented`, no la
contractable: si el instrumento lee el artefacto del que trata la tecnica
(codigo, build, historial) o un registro que llena una persona (tablero,
diario).

| Libro | contractable | instrumented |
|---|---|---|
| Codigo Limpio | 48% | **48%** |
| Arquitectura Java solida | 45% | **45%** |
| Scrum y eXtreme Programming | 25,5% | **14,4%** |
| Proyectos Agiles con Scrum | 26% | **3,4%** |
| Habitos Atomicos | 8,7% | **0%** |

La distribucion es bimodal: las tecnicas sobre codigo dan 40-55%, las tecnicas
sobre personas o proceso dan 0-3%. Nada en el medio. Scrum+XP cae en 14,4% no
por ser intermedio sino por ser **mezcla**: su capitulo de Refactoring da 55% y
sus capitulos de Scrum dan 0%.

Por eso el ruteo se decide **por seccion, no por libro**: el grafo OKF es uno
solo para todo el libro, y los contratos cuelgan solo donde hay instrumento.
