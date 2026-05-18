# Contrato común de datos — TPI Detector de Tendencias

Este documento define los nombres de campos y estructuras mínimas que deben respetar todos los integrantes del grupo.

## Entidades principales

El sistema trabaja con las siguientes entidades:

- Usuario
- Producto
- Categoría
- Evento
- Tendencia

## Identificadores obligatorios

Todos los módulos deben usar estos nombres de campos:

| Campo | Descripción |
|---|---|
| usuario_id | Identificador único del usuario |
| producto_id | Identificador único del producto |
| categoria_id | Identificador único de la categoría |
| evento_id | Identificador único del evento |
| tipo_evento | Tipo de interacción realizada |
| timestamp | Fecha y hora del evento |

## Tipos de evento válidos

Los tipos de evento permitidos son:

```text
vista
click
busqueda
compra
favorito