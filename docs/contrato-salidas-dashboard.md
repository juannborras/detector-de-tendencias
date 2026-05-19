# Contrato de salidas para Dashboard

Este documento define el formato que debe devolver cada módulo de consultas para que el dashboard pueda consumir la información sin depender de cómo está implementada cada base de datos por dentro.

La idea es que cada responsable de motor implemente una función específica que devuelva un diccionario de Python con una estructura fija.

---

## 1. Regla general

Cada archivo de consultas debe tener dos funciones:

```python
run_*_queries()
get_*_dashboard_data()
```

La función `run_*_queries()` sirve para mostrar resultados por consola.

La función `get_*_dashboard_data()` sirve para devolver datos estructurados al dashboard.

Ejemplo:

```python
def run_mongo_queries():
    data = get_mongo_dashboard_data()
    print(data)
    return data


def get_mongo_dashboard_data():
    return {
        "status": "ok",
        "counts": {},
        "datos": []
    }
```

El dashboard no debería depender de prints. Tiene que consumir datos devueltos por funciones.

---

## 2. Estados posibles

Todas las funciones de dashboard deben devolver un campo `status`.

Valores posibles:

```text
ok
pending
error
```

### `ok`

Significa que la consulta fue implementada correctamente y devuelve datos reales.

```python
"status": "ok"
```

### `pending`

Significa que la función todavía no fue implementada.

```python
"status": "pending"
```

### `error`

Significa que la función intentó consultar la base, pero ocurrió un error.

```python
"status": "error"
```

---

# 3. Salida esperada de MongoDB

## Archivo

```text
app/queries/mongo_queries.py
```

## Función obligatoria

```python
get_mongo_dashboard_data()
```

## Qué debe representar

MongoDB guarda los datos maestros/documentales del sistema:

```text
usuarios
productos
categorías
```

Por eso, su salida debe mostrar cantidad de documentos, distribución de productos por categoría y algunos ejemplos útiles del catálogo.

## Formato esperado

```python
{
    "status": "ok",
    "counts": {
        "usuarios": 50,
        "productos": 180,
        "categorias": 20
    },
    "productos_por_categoria": [
        {
            "categoria_id": "cat_001",
            "categoria": "Gaming",
            "total": 12
        }
    ],
    "productos_mayor_precio": [
        {
            "producto_id": "prod_010",
            "nombre": "Notebook Lenovo 10",
            "precio": 450000.0
        }
    ],
    "stock_bajo": [
        {
            "producto_id": "prod_023",
            "nombre": "Mouse Logitech 23",
            "stock": 3
        }
    ]
}
```

## Campos esperados

| Campo | Descripción |
|---|---|
| `status` | Estado de la consulta |
| `counts.usuarios` | Cantidad de usuarios en MongoDB |
| `counts.productos` | Cantidad de productos en MongoDB |
| `counts.categorias` | Cantidad de categorías en MongoDB |
| `productos_por_categoria` | Lista con cantidad de productos por categoría |
| `productos_mayor_precio` | Lista de productos más caros |
| `stock_bajo` | Lista de productos con poco stock |

## Placeholder válido mientras no esté implementado

```python
{
    "status": "pending",
    "message": "MongoDB dashboard data pendiente de implementación",
    "counts": {
        "usuarios": 0,
        "productos": 0,
        "categorias": 0
    },
    "productos_por_categoria": [],
    "productos_mayor_precio": [],
    "stock_bajo": []
}
```

---

# 4. Salida esperada de Cassandra

## Archivo

```text
app/queries/cassandra_queries.py
```

## Función obligatoria

```python
get_cassandra_dashboard_data()
```

## Qué debe representar

Cassandra guarda los eventos históricos del sistema. Como Cassandra se modela por consulta, un mismo evento lógico puede estar repetido físicamente en varias tablas.

Las tablas principales son:

```text
eventos_por_producto
eventos_por_usuario
eventos_por_categoria
eventos_por_tipo
resumen_diario
tendencias_por_categoria_fecha
```

## Formato esperado

```python
{
    "status": "ok",
    "counts": {
        "eventos_logicos": 750,
        "eventos_por_producto": 750,
        "eventos_por_usuario": 750,
        "eventos_por_categoria": 750,
        "eventos_por_tipo": 750,
        "resumen_diario": 400,
        "tendencias_por_categoria_fecha": 400
    },
    "eventos_por_tipo": [
        {
            "tipo_evento": "vista",
            "total": 330
        },
        {
            "tipo_evento": "click",
            "total": 180
        }
    ],
    "top_tendencias_categoria_fecha": [
        {
            "categoria_id": "cat_003",
            "fecha": "2026-05-01",
            "producto_id": "prod_010",
            "score_tendencia": 27.0,
            "total_eventos": 8
        }
    ],
    "resumen_diario_sample": [
        {
            "fecha": "2026-05-01",
            "producto_id": "prod_010",
            "categoria_id": "cat_003",
            "total_eventos": 8,
            "total_vistas": 3,
            "total_clicks": 2,
            "total_busquedas": 1,
            "total_compras": 2,
            "score_tendencia": 27.0
        }
    ]
}
```

## Campos esperados

| Campo | Descripción |
|---|---|
| `status` | Estado de la consulta |
| `counts.eventos_logicos` | Cantidad de eventos generados por el dataset |
| `counts.eventos_por_producto` | Filas en tabla eventos por producto |
| `counts.eventos_por_usuario` | Filas en tabla eventos por usuario |
| `counts.eventos_por_categoria` | Filas en tabla eventos por categoría |
| `counts.eventos_por_tipo` | Filas en tabla eventos por tipo |
| `counts.resumen_diario` | Filas resumen generadas |
| `counts.tendencias_por_categoria_fecha` | Filas de tendencias generadas |
| `eventos_por_tipo` | Cantidad de eventos agrupados por tipo |
| `top_tendencias_categoria_fecha` | Productos tendencia por categoría y fecha |
| `resumen_diario_sample` | Muestra de resúmenes diarios |

## Placeholder válido mientras no esté implementado

```python
{
    "status": "pending",
    "message": "Cassandra dashboard data pendiente de implementación",
    "counts": {
        "eventos_logicos": 0,
        "eventos_por_producto": 0,
        "eventos_por_usuario": 0,
        "eventos_por_categoria": 0,
        "eventos_por_tipo": 0,
        "resumen_diario": 0,
        "tendencias_por_categoria_fecha": 0
    },
    "eventos_por_tipo": [],
    "top_tendencias_categoria_fecha": [],
    "resumen_diario_sample": []
}
```

---

# 5. Salida esperada de Redis

## Archivo

```text
app/queries/redis_queries.py
```

## Función obligatoria

```python
get_redis_dashboard_data()
```

## Qué debe representar

Redis guarda información rápida y derivada:

```text
ranking global
ranking por categoría
cache top 10
contador total de eventos
sesiones temporales
```

Claves principales:

```text
trending:global
trending:cat:<categoria_id>
cache:top10_global
contador:eventos_total
sesion:<usuario_id>
```

## Formato esperado

```python
{
    "status": "ok",
    "contador_eventos": 750,
    "top_global": [
        {
            "producto_id": "prod_010",
            "score": 52.0
        },
        {
            "producto_id": "prod_033",
            "score": 47.0
        }
    ],
    "top_por_categoria": {
        "cat_001": [
            {
                "producto_id": "prod_010",
                "score": 20.0
            }
        ],
        "cat_002": [
            {
                "producto_id": "prod_025",
                "score": 18.0
            }
        ]
    },
    "cache_top10_global": [
        {
            "producto_id": "prod_010",
            "score": 52.0
        },
        {
            "producto_id": "prod_033",
            "score": 47.0
        }
    ],
    "sesiones_sample": [
        {
            "usuario_id": "usr_001",
            "email": "usuario001@example.com",
            "eventos_generados": "15",
            "ultima_actividad": "2026-05-12T10:30:00"
        }
    ]
}
```

## Campos esperados

| Campo | Descripción |
|---|---|
| `status` | Estado de la consulta |
| `contador_eventos` | Total de eventos procesados en Redis |
| `top_global` | Ranking global de productos |
| `top_por_categoria` | Ranking de productos agrupado por categoría |
| `cache_top10_global` | Top 10 guardado en cache |
| `sesiones_sample` | Muestra de sesiones de usuarios |

## Placeholder válido mientras no esté implementado

```python
{
    "status": "pending",
    "message": "Redis dashboard data pendiente de implementación",
    "contador_eventos": 0,
    "top_global": [],
    "top_por_categoria": {},
    "cache_top10_global": [],
    "sesiones_sample": []
}
```

---

# 6. Salida esperada de Neo4j

## Archivo

```text
app/queries/neo4j_queries.py
```

## Función obligatoria

```python
get_neo4j_dashboard_data()
```

## Qué debe representar

Neo4j guarda el grafo del sistema:

```text
usuarios
productos
categorías
relaciones de interacción
relaciones de interés
```

Nodos:

```text
(:Usuario)
(:Producto)
(:Categoria)
```

Relaciones:

```text
(:Producto)-[:PERTENECE_A]->(:Categoria)

(:Usuario)-[:VIO]->(:Producto)
(:Usuario)-[:CLICK]->(:Producto)
(:Usuario)-[:BUSCO]->(:Producto)
(:Usuario)-[:FAVORITO]->(:Producto)
(:Usuario)-[:COMPRO]->(:Producto)

(:Usuario)-[:INTERESADO_EN]->(:Categoria)
```

## Formato esperado

```python
{
    "status": "ok",
    "counts": {
        "usuarios": 50,
        "productos": 180,
        "categorias": 20,
        "relaciones_interaccion": 620,
        "eventos_representados": 750
    },
    "relaciones_por_tipo": [
        {
            "tipo": "VIO",
            "total_relaciones": 300,
            "total_eventos": 330
        },
        {
            "tipo": "CLICK",
            "total_relaciones": 160,
            "total_eventos": 180
        }
    ],
    "usuarios_mas_activos": [
        {
            "usuario_id": "usr_001",
            "nombre": "Juan Pérez",
            "eventos": 25
        }
    ],
    "productos_mas_conectados": [
        {
            "producto_id": "prod_010",
            "nombre": "Notebook Lenovo 10",
            "interacciones": 31
        }
    ],
    "recomendaciones_sample": [
        {
            "usuario_id": "usr_001",
            "producto_recomendado": "prod_033",
            "motivo": "Categoría de interés compartida"
        }
    ]
}
```

## Campos esperados

| Campo | Descripción |
|---|---|
| `status` | Estado de la consulta |
| `counts.usuarios` | Cantidad de nodos Usuario |
| `counts.productos` | Cantidad de nodos Producto |
| `counts.categorias` | Cantidad de nodos Categoria |
| `counts.relaciones_interaccion` | Cantidad de relaciones usuario-producto |
| `counts.eventos_representados` | Suma de eventos representados por las relaciones |
| `relaciones_por_tipo` | Relaciones agrupadas por tipo |
| `usuarios_mas_activos` | Usuarios con mayor cantidad de interacciones |
| `productos_mas_conectados` | Productos con mayor cantidad de interacciones |
| `recomendaciones_sample` | Muestra de recomendaciones simples |

## Placeholder válido mientras no esté implementado

```python
{
    "status": "pending",
    "message": "Neo4j dashboard data pendiente de implementación",
    "counts": {
        "usuarios": 0,
        "productos": 0,
        "categorias": 0,
        "relaciones_interaccion": 0,
        "eventos_representados": 0
    },
    "relaciones_por_tipo": [],
    "usuarios_mas_activos": [],
    "productos_mas_conectados": [],
    "recomendaciones_sample": []
}
```

---

# 7. Agregador del dashboard

El dashboard no debería conectarse directamente a cada base.

Debe pedir los datos a una función central:

```python
get_dashboard_data()
```

Esta función estará en:

```text
app/dashboard/dashboard_data.py
```

Y debe devolver:

```python
{
    "mongo": get_mongo_dashboard_data(),
    "cassandra": get_cassandra_dashboard_data(),
    "redis": get_redis_dashboard_data(),
    "neo4j": get_neo4j_dashboard_data()
}
```

De esa forma, el dashboard consume una única estructura general.

---

# 8. Reglas para los responsables

Cada responsable debe respetar estas reglas:

```text
1. No cambiar nombres de claves principales.
2. No devolver solo prints.
3. No devolver datos con estructuras inventadas.
4. No generar datos propios para su base.
5. Usar el dataset común cargado por LOAD.
6. Si todavía no terminó su parte, devolver status = "pending".
7. Si ocurre error, devolver status = "error" y un mensaje.
```

---

# 9. Flujo esperado

El flujo completo del proyecto debería ser:

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

El dashboard debe funcionar aunque alguna base todavía tenga datos pendientes. En ese caso, mostrará `pending` en vez de romperse.

---

# 10. Resumen final

Cada base puede tener consultas internas completamente distintas, pero todas deben devolver una salida compatible con este contrato.

La idea es:

```text
Cada responsable consulta su base como quiera.
Pero hacia afuera todos devuelven una estructura conocida.
```

Esto permite integrar el dashboard sin tener que reescribirlo cada vez que alguien cambia una query.