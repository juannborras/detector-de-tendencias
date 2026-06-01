# Operaciones CRUD en vivo

Este documento describe las operaciones agregadas para demostrar que el
programa no depende de datos fijos. La pantalla esta disponible en el
dashboard, en la pestana **Operaciones CRUD**.

## Criterio de no hardcodeo

En la demo, los valores de negocio no salen del codigo. El usuario ingresa los
IDs, fechas, scores, nombres y metricas desde el dashboard.

El codigo puede tener nombres de colecciones, tablas, labels o claves porque
son parte del modelo fisico de cada motor. Lo que no queda fijo para la demo
son los datos operativos que se cargan, actualizan o eliminan.

Las consultas de lectura tambien evitan IDs fijos:

- MongoDB toma IDs reales existentes cuando corre `run_mongo_queries()`.
- Cassandra toma una fila real existente para resolver particiones de ejemplo.
- Redis usa limites configurables desde `.env`.
- Neo4j usa limites configurables desde `.env` y parametros Cypher.

## Pantalla de dashboard

Archivo:

```text
app/dashboard/app.py
```

La pantalla se organiza por motor:

- MongoDB
- Cassandra
- Redis
- Neo4j

Cada operacion muestra:

- comando o consulta ejecutada
- parametros ingresados
- lectura de verificacion posterior
- estado `VERIFICADO` si la base confirma el cambio

## MongoDB

Archivo:

```text
app/crud_operations.py
```

### Operacion 1: crear o actualizar producto

Funcion:

```python
mongo_upsert_product(...)
```

Comando:

```python
db.productos.update_one(
    {"producto_id": producto_id},
    {"$set": producto},
    upsert=True
)
```

Datos ingresados en vivo:

- `producto_id`
- `nombre`
- `categoria_id`
- `marca`
- `precio`
- `stock`

Verificacion:

```python
db.productos.find_one({"producto_id": producto_id}, {"_id": 0})
```

Si el documento aparece en la lectura posterior, la operacion queda
verificada.

### Operacion 2: eliminar producto

Funcion:

```python
mongo_delete_product(producto_id)
```

Comando:

```python
db.productos.delete_one({"producto_id": producto_id})
```

Verificacion:

```python
db.productos.find_one({"producto_id": producto_id}, {"_id": 0})
```

Si la lectura devuelve `None`, la eliminacion queda verificada.

## Cassandra

Archivo:

```text
app/crud_operations.py
```

Tabla usada:

```text
resumen_diario
```

Se eligio esta tabla porque tiene una clave clara para demo:

```text
PRIMARY KEY ((fecha), producto_id)
```

### Operacion 1: crear o actualizar resumen diario

Funcion:

```python
cassandra_upsert_daily_summary(...)
```

Comando:

```sql
INSERT INTO resumen_diario (
    fecha, producto_id, categoria_id, total_eventos,
    total_vistas, total_clicks, total_busquedas,
    total_favoritos, total_compras, score_tendencia
)
VALUES (...)
```

En Cassandra, `INSERT` funciona como upsert: si la fila no existe la crea, y si
existe la actualiza para esa clave.

Datos ingresados en vivo:

- `fecha`
- `producto_id`
- `categoria_id`
- `total_eventos`
- `total_vistas`
- `total_clicks`
- `total_busquedas`
- `total_favoritos`
- `total_compras`
- `score_tendencia`

Verificacion:

```sql
SELECT *
FROM resumen_diario
WHERE fecha = ? AND producto_id = ?
```

Si la fila aparece en la lectura posterior, la operacion queda verificada.

### Operacion 2: eliminar resumen diario

Funcion:

```python
cassandra_delete_daily_summary(fecha, producto_id)
```

Comando:

```sql
DELETE FROM resumen_diario
WHERE fecha = ? AND producto_id = ?
```

Verificacion:

```sql
SELECT fecha, producto_id
FROM resumen_diario
WHERE fecha = ? AND producto_id = ?
```

Si la lectura no devuelve fila, la eliminacion queda verificada.

## Redis

Archivo:

```text
app/crud_operations.py
```

Estructura usada:

```text
trending:global
```

Es un sorted set donde el miembro es `producto_id` y el score es la puntuacion
de tendencia.

### Operacion 1: crear o actualizar score global

Funcion:

```python
redis_upsert_global_score(producto_id, score)
```

Comando:

```text
ZADD trending:global score producto_id
```

Verificacion:

```text
ZSCORE trending:global producto_id
```

Si Redis devuelve un score, la operacion queda verificada.

### Operacion 2: eliminar score global

Funcion:

```python
redis_delete_global_score(producto_id)
```

Comando:

```text
ZREM trending:global producto_id
```

Verificacion:

```text
ZSCORE trending:global producto_id
```

Si Redis devuelve `null`, la eliminacion queda verificada.

## Neo4j

Archivo:

```text
app/crud_operations.py
```

Labels y relacion usados:

```text
(:Producto)
(:Categoria)
(:Producto)-[:PERTENECE_A]->(:Categoria)
```

### Operacion 1: crear o actualizar producto

Funcion:

```python
neo4j_upsert_product(...)
```

Cypher:

```cypher
MERGE (p:Producto {producto_id: $producto_id})
SET p.nombre = $nombre,
    p.categoria_id = $categoria_id,
    p.marca = $marca,
    p.precio = $precio,
    p.stock = $stock,
    p.fecha_alta = coalesce(p.fecha_alta, datetime())
WITH p
MERGE (c:Categoria {categoria_id: $categoria_id})
ON CREATE SET c.nombre = $categoria_id
MERGE (p)-[:PERTENECE_A]->(c)
RETURN p.producto_id AS producto_id
```

Datos ingresados en vivo:

- `producto_id`
- `nombre`
- `categoria_id`
- `marca`
- `precio`
- `stock`

Verificacion:

```cypher
MATCH (p:Producto {producto_id: $producto_id})
OPTIONAL MATCH (p)-[:PERTENECE_A]->(c:Categoria)
RETURN p, c.categoria_id AS categoria_relacionada
```

Si el nodo aparece en la lectura posterior, la operacion queda verificada.

### Operacion 2: eliminar producto

Funcion:

```python
neo4j_delete_product(producto_id)
```

Cypher:

```cypher
MATCH (p:Producto {producto_id: $producto_id})
DETACH DELETE p
```

Verificacion:

```cypher
MATCH (p:Producto {producto_id: $producto_id})
RETURN p.producto_id AS producto_id
```

Si la lectura no devuelve nodo, la eliminacion queda verificada.

## Flujo recomendado para mostrar en clase

1. Abrir el dashboard con:

```bash
python -m app.main dashboard
```

2. Entrar en **Operaciones CRUD**.
3. Usar un `producto_id` nuevo para crear o actualizar.
4. Leer el bloque JSON que devuelve el programa y mostrar `verification`.
5. Entrar a la base correspondiente y ejecutar la consulta de verificacion.
6. Ejecutar la eliminacion con el mismo ID.
7. Volver a verificar que ya no existe.

Este flujo demuestra que el programa escribe, actualiza, elimina y vuelve a
leer desde la base real, en vez de mostrar resultados prearmados.
