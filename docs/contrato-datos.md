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
```

## Reglas de distribucion del dataset

Para que las consultas por categoria sean utiles en consola y en el dashboard,
el dataset debe cumplir esta regla minima:

```text
Cada categoria debe tener al menos 5 productos asociados.
```

Ademas, los nombres base de los productos deben ser coherentes con la
categoria asignada. Por ejemplo, una impresora debe pertenecer a Oficina o
Computacion, no a Deportes.

Las marcas tambien deben ser coherentes con la categoria. Cada categoria define
un conjunto chico de marcas validas para evitar combinaciones poco realistas,
por ejemplo una pelota de futbol marca Lenovo.
