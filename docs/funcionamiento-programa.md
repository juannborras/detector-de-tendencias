# Funcionamiento general del programa

Este documento explica como se levanta y ejecuta el proyecto del TPI
Detector de Tendencias, desde la preparacion del entorno local hasta la
ejecucion de las consultas.

La idea central del sistema es usar un mismo dataset logico y cargarlo en
distintas bases NoSQL, cada una elegida por un motivo distinto:

| Base | Rol dentro del TPI |
|---|---|
| MongoDB | Guarda datos maestros/documentales: usuarios, productos y categorias |
| Cassandra | Guarda eventos historicos modelados por consulta |
| Redis | Rankings, cache, contadores y sesiones |
| Neo4j | Relaciones entre usuarios, productos y categorias |

---

## 1. Preparacion del entorno Python

El proyecto esta pensado para ejecutarse desde un entorno virtual local.

Desde la raiz del proyecto:

```powershell
python -m venv .venv
```

Activar el entorno virtual:

```powershell
.\.venv\Scripts\Activate.ps1
```

Instalar dependencias:

```powershell
pip install -r requirements.txt
```

Las dependencias principales son:

| Dependencia | Uso |
|---|---|
| pymongo | Conexion y consultas a MongoDB |
| cassandra-driver | Conexion y consultas a Cassandra |
| redis | Conexion a Redis |
| neo4j | Conexion a Neo4j |
| python-dotenv | Lectura del archivo `.env` |
| faker | Generacion de datos ficticios |
| pandas, dash, plotly | Base para futuras visualizaciones |

---

## 2. Configuracion del proyecto

La configuracion se toma desde el archivo `.env`.

Si todavia no existe, se puede crear copiando el ejemplo:

```powershell
Copy-Item .env.example .env
```

Variables importantes:

```text
TOTAL_USUARIOS=50
TOTAL_PRODUCTOS=180
TOTAL_CATEGORIAS=20
TOTAL_EVENTOS=1250
EXPECTED_TOTAL_REGISTROS=1500
MIN_PRODUCTOS_POR_CATEGORIA=5
DATA_SEED=42
LOAD_MODE=reset
```

Con esta configuracion, el dataset logico queda compuesto por:

```text
50 usuarios
180 productos
20 categorias
1250 eventos
= 1500 registros logicos
```

La variable `MIN_PRODUCTOS_POR_CATEGORIA=5` garantiza que cada categoria
tenga al menos 5 productos asociados. Esto es importante para que las
consultas por categoria siempre devuelvan informacion util.

Los nombres base de los productos tambien se eligen segun la categoria. De esa
forma, una categoria como Deportes genera productos deportivos y una categoria
como Oficina puede generar impresoras, escritorios o sillas ergonomicas.

Las marcas se eligen con la misma regla: cada categoria tiene 3 marcas
posibles, y algunas se repiten cuando tiene sentido para categorias cercanas
como Gaming, Tecnologia, Audio, Oficina y Computacion.

---

## 3. Levantar las bases con Docker Compose

Las bases se ejecutan en contenedores Docker.

```powershell
docker compose up -d
```

Contenedores esperados:

| Contenedor | Puerto | Uso |
|---|---:|---|
| tpi_mongo | 27017 | MongoDB |
| tpi_cassandra | 9042 | Cassandra |
| tpi_redis | 6379 | Redis |
| tpi_neo4j | 7474 / 7687 | Neo4j |

Para verificar conectividad:

```powershell
python -m app.main test
```

Ese comando prueba una conexion simple contra cada motor.

---

## 4. Setup de estructuras

Antes de cargar datos, hay que crear colecciones, indices, tablas, claves
de metadata y constraints.

```powershell
python -m app.main setup
```

Internamente, `setup_all()` ejecuta:

| Base | Funcion |
|---|---|
| MongoDB | `setup_mongo()` |
| Cassandra | `setup_cassandra()` |
| Redis | `setup_redis()` |
| Neo4j | `setup_neo4j()` |

### MongoDB

Crea las colecciones:

```text
usuarios
productos
categorias
```

Tambien crea indices para campos usados en consultas:

```text
productos.producto_id
productos.categoria_id
productos.nombre
usuarios.usuario_id
usuarios.email
categorias.categoria_id
categorias.nombre
```

### Cassandra

Crea el keyspace configurado y tablas modeladas por consulta:

```text
eventos_por_producto
eventos_por_usuario
eventos_por_categoria
eventos_por_tipo
resumen_diario
tendencias_por_categoria_fecha
```

Cassandra no se modela como una base relacional general. En este proyecto,
cada tabla responde a una pregunta concreta. Por eso un mismo evento logico
se replica fisicamente en varias tablas.

### Redis

Pendiente a nivel consultas finales. El setup registra convenciones de claves
para rankings, cache, contador y sesiones.

### Neo4j

Pendiente a nivel consultas finales. El setup crea constraints e indices para
nodos `Usuario`, `Producto` y `Categoria`.

---

## 5. Generacion del dataset comun

Para ver el dataset generado sin cargarlo:

```powershell
python -m app.main generate
```

El generador crea:

| Entidad | Cantidad |
|---|---:|
| usuarios | 50 |
| productos | 180 |
| categorias | 20 |
| eventos | 1250 |

El dataset se genera una sola vez durante la carga general y despues se pasa
a todos los loaders. Esto asegura que todas las bases trabajen con los mismos
IDs de usuarios, productos y categorias.

---

## 6. Carga de datos

Para cargar todas las bases:

```powershell
python -m app.main load
```

El flujo esta centralizado en `load_all()`:

```text
generate_dataset()
load_mongo(dataset)
load_cassandra(dataset)
load_redis(dataset)
load_neo4j(dataset)
```

### MongoDB durante la carga

MongoDB recibe los datos maestros:

```text
usuarios
productos
categorias
```

Cada documento se inserta o actualiza usando `update_one(..., upsert=True)`.
Si `LOAD_MODE=reset`, antes se eliminan los documentos anteriores.

MongoDB queda como fuente documental para responder preguntas de catalogo,
por ejemplo:

```text
Cuantos productos hay?
Que productos tienen bajo stock?
Cuantos productos tiene cada categoria?
Cual es la informacion completa de un producto o usuario?
```

### Cassandra durante la carga

Cassandra recibe los eventos historicos.

Por cada evento logico, se insertan filas en tablas distintas:

```text
eventos_por_producto
eventos_por_usuario
eventos_por_categoria
eventos_por_tipo
```

Ademas, el loader calcula resumenes diarios:

```text
resumen_diario
tendencias_por_categoria_fecha
```

Esto permite consultar eventos de manera eficiente respetando las partition
keys de Cassandra.

### Redis durante la carga

Pendiente a nivel consultas finales.

La carga existente procesa eventos para estructuras derivadas como:

```text
trending:global
trending:cat:<categoria_id>
cache:top10_global
contador:eventos_total
sesion:<usuario_id>
```

### Neo4j durante la carga

Pendiente a nivel consultas finales.

La carga existente crea nodos y relaciones:

```text
(:Usuario)
(:Producto)
(:Categoria)
(:Producto)-[:PERTENECE_A]->(:Categoria)
(:Usuario)-[:VIO|CLICK|BUSCO|FAVORITO|COMPRO]->(:Producto)
(:Usuario)-[:INTERESADO_EN]->(:Categoria)
```

---

## 7. Validacion

Para validar que las bases coinciden con la configuracion:

```powershell
python -m app.main validate
```

La validacion revisa:

| Base | Validacion |
|---|---|
| Configuracion | Total logico esperado: 1500 |
| MongoDB | 50 usuarios, 180 productos, 20 categorias, minimo 5 productos por categoria, coherencia producto-categoria y coherencia marca-categoria |
| Cassandra | 1250 eventos en tablas principales y resumenes con filas |
| Redis | Valida contador, ranking global, cache y sesiones |
| Neo4j | Valida nodos, relaciones y eventos representados |

---

## 8. Ejecucion de consultas

Para ejecutar consultas de demostracion:

```powershell
python -m app.main queries
```

El punto central es `run_all_queries()`, que llama a:

```text
run_mongo_queries()
run_cassandra_queries()
run_redis_queries()
run_neo4j_queries()
```

### Consultas MongoDB

MongoDB tiene una funcion por consulta, para mantener el mismo estilo que
Cassandra y facilitar la explicacion oral.

Consultas implementadas:

| Funcion | Que muestra |
|---|---|
| `query_counts()` | Cantidad de usuarios, productos y categorias |
| `query_productos_mayor_precio()` | Productos mas caros |
| `query_stock_bajo()` | Productos con stock menor al umbral configurado |
| `query_productos_por_categoria()` | Cantidad de productos por categoria usando aggregation |
| `query_categoria_por_id()` | Informacion de una categoria por `categoria_id` |
| `query_producto_por_id()` | Informacion de un producto por `producto_id` |
| `query_usuario_por_id()` | Informacion de un usuario por `usuario_id` |

`run_mongo_queries()` toma IDs reales desde las colecciones antes de ejecutar
las consultas por ID. De esa forma no depende de `categoria_id`, `producto_id`
o `usuario_id` escritos a mano en el codigo.

En el dashboard, esas consultas tambien se pueden ejecutar desde inputs: se
escribe un `categoria_id`, `producto_id` o `usuario_id` y la pantalla muestra el
documento encontrado.

### Consultas Cassandra

Cassandra tambien tiene una funcion por consulta:

| Funcion | Que muestra |
|---|---|
| `query_eventos_por_producto()` | Eventos de un producto en una fecha |
| `query_eventos_por_usuario()` | Eventos de un usuario en una fecha |
| `query_eventos_por_categoria()` | Eventos de una categoria en una fecha |
| `query_eventos_por_tipo()` | Eventos de un tipo en una fecha |
| `query_resumen_diario()` | Resumen diario por producto |
| `query_tendencias_por_categoria_fecha()` | Top de tendencias por categoria y fecha |
| `query_top_tendencias_resumen_diario()` | Top diario de productos tendencia basado en resumen_diario |

Estas consultas usan muestras reales existentes para evitar hardcodear
producto, usuario o fecha que no tengan datos.

En el caso del dashboard, `query_resumen_diario()` y
`query_top_tendencias_resumen_diario()` tambien aceptan una fecha como
parametro. Las opciones de fecha se obtienen desde `resumen_diario`, por lo que
solo se muestran fechas que existen en Cassandra y que fueron generadas a partir
de eventos reales.

El score de tendencia se calcula con esta formula:

```text
score = vistas*1 + clicks*2 + busquedas*3 + favoritos*4 + compras*5
```

Por eso `total_favoritos` forma parte de los resumenes diarios. Si no se
muestra esa columna, el score puede parecer incorrecto aunque este bien
calculado.

### Consultas Redis

Redis consulta el ranking global, rankings por categoria, cache, contador de
eventos y sesiones de usuario. Los tamanos de muestra se toman desde variables
de configuracion (`QUERY_TOP_LIMIT`, `QUERY_CATEGORY_TOP_LIMIT` y
`QUERY_SAMPLE_LIMIT`), no desde valores de demo escritos dentro de la consulta.

### Consultas Neo4j

Neo4j consulta conteos del grafo, usuarios mas activos, productos con mas
eventos del tipo elegido, categorias con mas interes, usuarios que realizaron
un evento sobre un producto y recomendaciones por categoria de interes. El
dashboard consume la salida generada por `run_neo4j_queries(show_output=False)`,
por lo que la lista de consultas vive en un unico punto.

---

## 9. Datos para dashboard

Ademas de imprimir por consola, cada motor debe exponer una funcion:

```text
get_*_dashboard_data()
```

Estas funciones devuelven diccionarios simples, pensados para que el dashboard
no dependa de prints ni de detalles internos de cada base.

El agregador central es:

```text
app/dashboard/dashboard_data.py
```

Y expone:

```python
get_dashboard_data()
```

La idea es que el dashboard consuma una unica estructura:

```python
{
    "mongo": ...,
    "cassandra": ...,
    "redis": ...,
    "neo4j": ...
}
```

Si una base todavia no tiene sus consultas finales, puede devolver
`status = "pending"` sin romper el resto.

El agregador tambien puede enriquecer datos para visualizacion. Por ejemplo,
cuando Cassandra devuelve `categoria_id`, el dashboard usa el catalogo maestro
de MongoDB para agregar `categoria_nombre` y mostrar tablas mas legibles sin
cambiar el modelo fisico de Cassandra.

La primera version del dashboard esta en:

```text
app/dashboard/app.py
```

Se levanta con:

```powershell
python -m app.main dashboard
```

El dashboard muestra:

| Seccion | Datos |
|---|---|
| Estado de motores | `ok`, `pending` o `error` para cada base |
| Lectura general | KPIs de usuarios, productos, categorias y eventos |
| Senales historicas | Eventos por tipo, score de tendencia y resumenes Cassandra |
| Top diario | Productos con mayor score dentro de la fecha elegida, calculados desde resumen_diario |
| Fecha de analisis | Selector armado con fechas reales disponibles en resumen_diario |
| Busqueda por ID | Consulta documental de categoria, producto y usuario desde inputs del dashboard |
| Catalogo documental | Distribucion de productos, stock bajo y productos caros MongoDB |
| Grafo de relaciones | Conteos, productos por evento, busqueda usuario-producto y recomendaciones Neo4j |
| Estado Redis | Ranking, cache, contador y sesiones |
| Operaciones CRUD | Pantalla separada para crear/actualizar y eliminar datos en vivo por motor |

Las operaciones CRUD estan documentadas en:

```text
docs/operaciones-crud.md
```

---

## 10. Flujo recomendado

El flujo completo de trabajo es:

```powershell
docker compose up -d
python -m app.main test
python -m app.main setup
python -m app.main generate
python -m app.main load
python -m app.main validate
python -m app.main queries
python -m app.main dashboard
```

Ese flujo levanta las bases, crea estructuras, genera el dataset comun, carga
los datos, valida coherencia, ejecuta las consultas de demostracion y abre el
dashboard web.

Con esto, el proyecto cumple la propuesta del TPI: detectar y explicar
tendencias ocultas a partir de eventos de usuarios, apoyandose en una
arquitectura poliglota donde cada base cumple un rol especifico.
