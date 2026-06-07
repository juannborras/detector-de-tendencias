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

Tablas usadas:

```text
resumen_diario
tendencias_por_categoria_fecha
```

Se usa `resumen_diario` como fuente del resumen visible en el dashboard y
`tendencias_por_categoria_fecha` como tabla denormalizada para el top por
categoria y fecha.

```text
resumen_diario: PRIMARY KEY ((fecha), producto_id)
tendencias_por_categoria_fecha: PRIMARY KEY ((categoria_id, fecha), score_tendencia, producto_id)
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

INSERT INTO tendencias_por_categoria_fecha (
    categoria_id, fecha, score_tendencia, producto_id,
    total_eventos, total_vistas, total_clicks,
    total_busquedas, total_favoritos, total_compras
)
VALUES (...)
```

En Cassandra, `INSERT` funciona como upsert: si la fila no existe la crea, y si
existe la actualiza para esa clave. Como `score_tendencia` forma parte de la
clave de clustering en `tendencias_por_categoria_fecha`, antes de insertar un
score nuevo se elimina la tendencia anterior del mismo `fecha + producto_id`.

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

SELECT *
FROM tendencias_por_categoria_fecha
WHERE categoria_id = ? AND fecha = ?
  AND score_tendencia = ? AND producto_id = ?
```

Si ambas lecturas aparecen en la verificacion posterior, la operacion queda
verificada.

### Operacion 2: eliminar resumen diario

Funcion:

```python
cassandra_delete_daily_summary(fecha, producto_id)
```

Comando:

```sql
DELETE FROM resumen_diario
WHERE fecha = ? AND producto_id = ?

DELETE FROM tendencias_por_categoria_fecha
WHERE categoria_id = ? AND fecha = ?
  AND score_tendencia = ? AND producto_id = ?
```

Verificacion:

```sql
SELECT fecha, producto_id
FROM resumen_diario
WHERE fecha = ? AND producto_id = ?

SELECT categoria_id, fecha, score_tendencia, producto_id
FROM tendencias_por_categoria_fecha
WHERE fecha = ? AND producto_id = ?
ALLOW FILTERING
```

Si ninguna lectura devuelve filas, la eliminacion queda verificada.

## Redis

Archivo:

```text
app/crud_operations.py
```

Estructuras usadas:

```text
trending:global
trending:cat:<categoria_id>
cache:top10_global
```

Son sorted sets donde el miembro es `producto_id` y el score es la puntuacion
de tendencia. El cache global se regenera despues de cada cambio para que el
dashboard muestre el mismo top que Redis guarda.

### Operacion 1: crear o actualizar score global

Funcion:

```python
redis_upsert_global_score(producto_id, score, categoria_id=None)
```

Comando:

```text
ZADD trending:global score producto_id
ZADD trending:cat:<categoria_id> score producto_id
SETEX cache:top10_global 3600 <top actual>
```

`categoria_id` se toma desde MongoDB si el producto existe en el catalogo. Si es
un producto nuevo que no existe en MongoDB, se carga desde el dashboard.

Verificacion:

```text
ZSCORE trending:global producto_id
ZSCORE trending:cat:<categoria_id> producto_id
```

Si ambos scores coinciden con el valor ingresado, la operacion queda verificada.

### Operacion 2: eliminar score global

Funcion:

```python
redis_delete_global_score(producto_id)
```

Comando:

```text
ZREM trending:global producto_id
ZREM trending:cat:* producto_id
SETEX cache:top10_global 3600 <top actual>
```

Verificacion:

```text
ZSCORE trending:global producto_id
ZSCORE trending:cat:* producto_id
```

Si Redis devuelve `null` en global y no queda ninguna categoria con ese
producto, la eliminacion queda verificada.

## Neo4j

Archivo:

```text
app/crud_operations.py
```

Labels y relaciones usados:

```text
(:Usuario)
(:Producto)
(:Usuario)-[:VIO|CLICK|BUSCO|FAVORITO|COMPRO]->(:Producto)
```

### Operacion 1: registrar o actualizar evento usuario-producto

Funcion:

```python
neo4j_upsert_user_event(usuario_id, producto_id, tipo_evento)
```

Cypher:

```cypher
MERGE (u:Usuario {usuario_id: $usuario_id})
MERGE (p:Producto {producto_id: $producto_id})
MERGE (u)-[r:<TIPO_EVENTO>]->(p)
ON CREATE SET r.cantidad = 1, r.fecha_ultima = datetime()
ON MATCH SET r.cantidad = coalesce(r.cantidad, 0) + 1,
              r.fecha_ultima = datetime()
RETURN u.usuario_id, p.producto_id, type(r), r.cantidad
```

Datos ingresados en vivo:

- `usuario_id`
- `producto_id`
- `tipo_evento`

`tipo_evento` acepta los tipos reales de relacion (`VIO`, `CLICK`, `BUSCO`,
`FAVORITO`, `COMPRO`) y alias de presentacion como `favoritos`, `compras` o
`clicks`.

Verificacion:

```cypher
MATCH (u:Usuario {usuario_id: $usuario_id})-[r:<TIPO_EVENTO>]->(p:Producto {producto_id: $producto_id})
RETURN u.usuario_id, p.producto_id, type(r), r.cantidad
```

Si la relacion aparece en la lectura posterior, la operacion queda verificada.

### Operacion 2: eliminar relacion usuario-producto

Funcion:

```python
neo4j_delete_user_event(usuario_id, producto_id, tipo_evento)
```

Cypher:

```cypher
MATCH (u:Usuario {usuario_id: $usuario_id})
MATCH (p:Producto {producto_id: $producto_id})
MATCH (u)-[r:<TIPO_EVENTO>]->(p)
DELETE r
```

Verificacion:

```cypher
MATCH (u:Usuario {usuario_id: $usuario_id})
MATCH (p:Producto {producto_id: $producto_id})
OPTIONAL MATCH (u)-[r:<TIPO_EVENTO>]->(p)
RETURN count(r) AS relaciones_restantes
```

Si `relaciones_restantes` es `0`, la eliminacion queda verificada.

## Flujo recomendado para mostrar en clase

1. Abrir el dashboard con:

```bash
python -m app.main dashboard
```

2. Entrar en **Operaciones CRUD**.
3. Usar valores ingresados en vivo para crear o actualizar.
4. Leer el bloque JSON que devuelve el programa y mostrar `verification`.
5. Entrar a la base correspondiente y ejecutar la consulta de verificacion.
6. Ejecutar la eliminacion con el mismo ID.
7. Volver a verificar que ya no existe.

Este flujo demuestra que el programa escribe, actualiza, elimina y vuelve a
leer desde la base real, en vez de mostrar resultados prearmados.
