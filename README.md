# TPI — Detector de Tendencias

Proyecto integrador de Ingeniería de Datos II.

El objetivo del sistema es detectar productos que empiezan a mostrar crecimiento de interés a partir de eventos de usuarios, como vistas, clicks, búsquedas, compras y favoritos.

## Arquitectura general

El proyecto utiliza una arquitectura políglota de bases de datos NoSQL.

La aplicación está desarrollada en Python y se conecta a cuatro motores de base de datos levantados con Docker Compose:

| Motor | Uso principal |
|---|---|
| MongoDB | Productos, usuarios y categorías en formato documental |
| Cassandra | Eventos históricos masivos, modelados por consulta |
| Redis | Rankings, cache, contadores y sesiones |
| Neo4j | Relaciones entre usuarios, productos y categorías |

## Infraestructura

Durante el desarrollo, la aplicación Python se ejecuta localmente desde el entorno virtual `.venv`.

Los motores de base de datos se ejecutan en contenedores Docker:

```text
tpi_mongo
tpi_redis
tpi_neo4j
tpi_cassandra