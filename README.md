# TPI - Detector de Tendencias

Proyecto integrador de Ingenieria de Datos II.

El objetivo del sistema es detectar productos que empiezan a mostrar crecimiento
de interes a partir de eventos de usuarios, como vistas, clicks, busquedas,
favoritos y compras.

## Arquitectura

El proyecto usa una arquitectura poliglota de bases de datos NoSQL:

| Motor | Uso principal |
| --- | --- |
| MongoDB | Productos, usuarios y categorias en formato documental |
| Cassandra | Eventos historicos masivos, modelados por consulta |
| Redis | Rankings, cache, contadores y sesiones |
| Neo4j | Relaciones entre usuarios, productos y categorias |

La aplicacion esta desarrollada en Python y expone un dashboard Dash en:

```text
http://127.0.0.1:8050
```

## Ejecucion recomendada con Docker

Esta es la forma mas simple para compartir el proyecto con otros integrantes.
Requiere Docker Desktop.

1. Levantar bases y app:

```bash
docker compose up -d --build
```

2. Crear estructuras:

```bash
docker compose run --rm app python -m app.main setup
```

3. Cargar datos:

```bash
docker compose run --rm app python -m app.main load
```

4. Validar datos:

```bash
docker compose run --rm app python -m app.main validate
```

5. Ejecutar consultas por consola:

```bash
docker compose run --rm app python -m app.main queries
```

6. Abrir dashboard:

```text
http://127.0.0.1:8050
```

Si Cassandra todavia esta iniciando, esperar uno o dos minutos y volver a correr
`setup` y `load`.

## Ejecucion local de desarrollo

Tambien se puede ejecutar Python localmente y usar Docker solo para las bases.

```bash
docker compose up -d mongo redis neo4j cassandra
python -m app.main test
python -m app.main setup
python -m app.main load
python -m app.main validate
python -m app.main queries
python -m app.main dashboard
```

## Servicios Docker

| Servicio | Contenedor | Puerto |
| --- | --- | --- |
| app | tpi_app | 8050 |
| mongo | tpi_mongo | 27017 |
| redis | tpi_redis | 6379 |
| neo4j | tpi_neo4j | 7474 / 7687 |
| cassandra | tpi_cassandra | 9042 |

## Estructura del proyecto

| Ruta | Responsabilidad |
| --- | --- |
| `app/connections.py` | Conexion a los cuatro motores |
| `app/models/` | Estructuras fisicas: indices, constraints, tablas y claves |
| `app/loaders/` | Carga del dataset comun en cada motor |
| `app/generators/catalog.json` | Catalogo semilla editable para categorias, marcas, eventos y atributos |
| `app/queries/` | Consultas demostrativas y datos para dashboard |
| `app/crud_operations.py` | Operaciones CRUD en vivo |
| `app/dashboard/` | Dashboard Dash |
| `app/validation/` | Validaciones de carga y coherencia |
| `docs/` | Documentacion e informes |

## Comandos utiles por base

MongoDB:

```bash
docker exec -it tpi_mongo mongosh tendencias_db
```

Cassandra:

```bash
docker exec -it tpi_cassandra cqlsh -k tendencias
```

Redis:

```bash
docker exec -it tpi_redis redis-cli
```

Neo4j:

```bash
docker exec -it tpi_neo4j cypher-shell -u neo4j -p neo4j123
```
