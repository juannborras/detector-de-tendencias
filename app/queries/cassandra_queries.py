from cassandra.util import Date

from app.config import CASSANDRA_KEYSPACE, TOTAL_EVENTOS
from app.connections import get_cassandra_session

EVENT_TYPES = ["vista", "click", "busqueda", "favorito", "compra"]

def serialize_value(value):
    """
    Convierte valores especiales de Cassandra a tipos simples.

    Cassandra puede devolver:
    - Date(...) para columnas tipo date
    - datetime para columnas tipo timestamp

    Esta función los transforma a strings legibles para consola,
    JSON y dashboard.
    """

    if value is None:
        return None

    # Cassandra date: aparece como Date(20587) si no lo convertimos
    if isinstance(value, Date):
        return value.date().isoformat()

    # datetime/date estándar de Python
    if hasattr(value, "isoformat"):
        return value.isoformat()

    return value

def count_table(session, table_name):
    """
    Cuenta filas de una tabla Cassandra.

    Para este TPI está bien usar COUNT(*) porque el dataset es chico.
    En producción, con millones de filas, no sería recomendable usarlo
    como consulta frecuente.
    """

    row = session.execute(
        f"SELECT COUNT(*) AS total FROM {table_name}"
    ).one()

    return row.total

def row_to_dict(row):
    """
    Convierte una fila de Cassandra en un diccionario de Python.
    Esto sirve para imprimir mejor y para devolver datos al dashboard.
    """

    return {
        key: serialize_value(value)
        for key, value in row._asdict().items()
    }


def get_sample_row(session, table_name):
    """
    Obtiene una fila cualquiera de una tabla.

    Esto se usa para tomar valores reales existentes, como producto_id y fecha,
    y evitar hardcodear un producto/fecha que capaz no tiene eventos.
    """

    return session.execute(
        f"SELECT * FROM {table_name} LIMIT 1"
    ).one()

def get_eventos_por_tipo_for_dashboard(session):
    """
    Devuelve la cantidad de eventos por tipo para una fecha existente.

    Importante:
    No hacemos un GROUP BY libre como en SQL.
    En Cassandra consultamos respetando la partition key:
    tipo_evento + fecha.
    """

    sample = get_sample_row(session, "eventos_por_tipo")

    if not sample:
        return []

    fecha = sample.fecha
    result = []

    for event_type in EVENT_TYPES:
        row = session.execute("""
                              SELECT COUNT(*) AS total
                              FROM eventos_por_tipo
                              WHERE tipo_evento = %s
                                AND fecha = %s
                              """, (event_type, fecha)).one()

        result.append({
            "tipo_evento": event_type,
            "fecha": serialize_value(fecha),
            "total": row.total
        })

    return result


def get_cassandra_dashboard_data():
    """
    Devuelve datos Cassandra para el dashboard.

    Esta función cumple el contrato definido en:
    docs/contrato-salidas-dashboard.md
    """

    cluster = None

    try:
        cluster, session = get_cassandra_session()
        session.set_keyspace(CASSANDRA_KEYSPACE)

        counts = {
            "eventos_logicos": TOTAL_EVENTOS,
            "eventos_por_producto": count_table(session, "eventos_por_producto"),
            "eventos_por_usuario": count_table(session, "eventos_por_usuario"),
            "eventos_por_categoria": count_table(session, "eventos_por_categoria"),
            "eventos_por_tipo": count_table(session, "eventos_por_tipo"),
            "resumen_diario": count_table(session, "resumen_diario"),
            "tendencias_por_categoria_fecha": count_table(
                session,
                "tendencias_por_categoria_fecha"
            ),
        }

        resumen = query_resumen_diario(session)
        tendencias = query_tendencias_por_categoria_fecha(session)

        return {
            "status": "ok",
            "counts": counts,
            "eventos_por_tipo": get_eventos_por_tipo_for_dashboard(session),
            "top_tendencias_categoria_fecha": tendencias["rows"],
            "resumen_diario_sample": resumen["rows"],
        }

    except Exception as error:
        return {
            "status": "error",
            "message": "Error al obtener datos de Cassandra para dashboard",
            "error": str(error),
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

    finally:
        if cluster:
            cluster.shutdown()

def run_cassandra_queries():
    """
    Ejecuta las 6 consultas Cassandra por consola.
    """

    cluster = None

    try:
        cluster, session = get_cassandra_session()
        session.set_keyspace(CASSANDRA_KEYSPACE)

        queries = [
            query_eventos_por_producto(session),
            query_eventos_por_usuario(session),
            query_eventos_por_categoria(session),
            query_eventos_por_tipo(session),
            query_resumen_diario(session),
            query_tendencias_por_categoria_fecha(session),
        ]

        print("Cassandra queries")
        print("=" * 60)

        for query in queries:
            print()
            print(query["descripcion"])
            print("-" * 60)
            print(f"Tabla: {query['query']}")
            print(f"Partition key usada: {query['partition_key']}")
            print(f"Filas devueltas: {len(query['rows'])}")

            for row in query["rows"][:5]:
                print(row)

        return queries

    except Exception as error:
        print("Cassandra queries ERROR")
        print(error)
        return []

    finally:
        if cluster:
            cluster.shutdown()

def query_eventos_por_producto(session):
    """
    Consulta 1:
    obtiene los eventos de un producto específico en una fecha específica.

    Tabla usada:
    eventos_por_producto

    Partition key:
    producto_id + fecha

    Clustering:
    timestamp DESC + evento_id

    Esta consulta demuestra el acceso correcto en Cassandra,
    porque usa la partition key completa.
    """

    sample = get_sample_row(session, "eventos_por_producto")

    if not sample:
        return {
            "query": "eventos_por_producto",
            "descripcion": "Eventos de un producto en una fecha",
            "partition_key": None,
            "rows": []
        }

    rows = session.execute("""
                           SELECT producto_id, fecha, timestamp, evento_id, usuario_id, tipo_evento, categoria_id
                           FROM eventos_por_producto
                           WHERE producto_id = %s
                             AND fecha = %s
                               LIMIT 10
                           """, (sample.producto_id, sample.fecha))

    return {
        "query": "eventos_por_producto",
        "descripcion": "Eventos de un producto en una fecha",
        "partition_key": {
            "producto_id": sample.producto_id,
            "fecha": serialize_value(sample.fecha)
        },
        "rows": [row_to_dict(row) for row in rows]
    }


def query_eventos_por_usuario(session):
    """
    Consulta 2:
    obtiene los eventos realizados por un usuario específico
    en una fecha específica.

    Tabla usada:
    eventos_por_usuario

    Partition key:
    usuario_id + fecha

    Clustering:
    timestamp DESC + evento_id

    Esta consulta demuestra cómo recuperar la actividad histórica
    de un usuario usando una tabla modelada para ese patrón de acceso.
    """

    sample = get_sample_row(session, "eventos_por_usuario")

    if not sample:
        return {
            "query": "eventos_por_usuario",
            "descripcion": "Eventos de un usuario en una fecha",
            "partition_key": None,
            "rows": []
        }

    rows = session.execute("""
        SELECT usuario_id, fecha, timestamp, evento_id, producto_id, tipo_evento, categoria_id
        FROM eventos_por_usuario
        WHERE usuario_id = %s
          AND fecha = %s
        LIMIT 10
    """, (sample.usuario_id, sample.fecha))

    return {
        "query": "eventos_por_usuario",
        "descripcion": "Eventos de un usuario en una fecha",
        "partition_key": {
            "usuario_id": sample.usuario_id,
            "fecha": serialize_value(sample.fecha)
        },
        "rows": [row_to_dict(row) for row in rows]
    }


def query_eventos_por_categoria(session):
    """
    Consulta 3:
    obtiene los eventos ocurridos dentro de una categoría específica
    en una fecha específica.

    Tabla usada:
    eventos_por_categoria

    Partition key:
    categoria_id + fecha

    Clustering:
    timestamp DESC + evento_id

    Esta consulta permite analizar la actividad histórica de una categoría,
    por ejemplo Gaming, Tecnología, Audio, etc.
    """

    sample = get_sample_row(session, "eventos_por_categoria")

    if not sample:
        return {
            "query": "eventos_por_categoria",
            "descripcion": "Eventos de una categoría en una fecha",
            "partition_key": None,
            "rows": []
        }

    rows = session.execute("""
        SELECT categoria_id, fecha, timestamp, evento_id, usuario_id, producto_id, tipo_evento
        FROM eventos_por_categoria
        WHERE categoria_id = %s
          AND fecha = %s
        LIMIT 10
    """, (sample.categoria_id, sample.fecha))

    return {
        "query": "eventos_por_categoria",
        "descripcion": "Eventos de una categoría en una fecha",
        "partition_key": {
            "categoria_id": sample.categoria_id,
            "fecha": serialize_value(sample.fecha)
        },
        "rows": [row_to_dict(row) for row in rows]
    }



def query_eventos_por_tipo(session):
    """
    Consulta 4:
    obtiene los eventos de un tipo específico en una fecha específica.

    Tabla usada:
    eventos_por_tipo

    Partition key:
    tipo_evento + fecha

    Clustering:
    timestamp DESC + evento_id

    Esta consulta permite analizar eventos por comportamiento:
    vistas, clicks, búsquedas, favoritos o compras.
    """

    sample = get_sample_row(session, "eventos_por_tipo")

    if not sample:
        return {
            "query": "eventos_por_tipo",
            "descripcion": "Eventos de un tipo en una fecha",
            "partition_key": None,
            "rows": []
        }

    rows = session.execute("""
        SELECT tipo_evento, fecha, timestamp, evento_id, usuario_id, producto_id, categoria_id
        FROM eventos_por_tipo
        WHERE tipo_evento = %s
          AND fecha = %s
        LIMIT 10
    """, (sample.tipo_evento, sample.fecha))

    return {
        "query": "eventos_por_tipo",
        "descripcion": "Eventos de un tipo en una fecha",
        "partition_key": {
            "tipo_evento": sample.tipo_evento,
            "fecha": serialize_value(sample.fecha)
        },
        "rows": [row_to_dict(row) for row in rows]
    }



def query_resumen_diario(session):
    """
    Consulta 5:
    obtiene el resumen diario de productos para una fecha específica.

    Tabla usada:
    resumen_diario

    Partition key:
    fecha

    Clustering:
    producto_id

    Esta tabla no guarda eventos individuales, sino métricas agregadas
    por producto y fecha.
    """

    sample = get_sample_row(session, "resumen_diario")

    if not sample:
        return {
            "query": "resumen_diario",
            "descripcion": "Resumen diario de productos",
            "partition_key": None,
            "rows": []
        }

    rows = session.execute("""
                           SELECT fecha, producto_id, categoria_id, total_eventos,
                                  total_vistas, total_clicks, total_busquedas,
                                  total_compras, score_tendencia
                           FROM resumen_diario
                           WHERE fecha = %s
                               LIMIT 10
                           """, (sample.fecha,))

    return {
        "query": "resumen_diario",
        "descripcion": "Resumen diario de productos",
        "partition_key": {
            "fecha": serialize_value(sample.fecha)
        },
        "rows": [row_to_dict(row) for row in rows]
    }

def query_tendencias_por_categoria_fecha(session):
    """
    Consulta 6:
    obtiene el top de productos tendencia dentro de una categoría
    en una fecha específica.

    Tabla usada:
    tendencias_por_categoria_fecha

    Partition key:
    categoria_id + fecha

    Clustering:
    score_tendencia DESC + producto_id

    Esta consulta es central para el objetivo del proyecto:
    detectar productos con mayor actividad dentro de una categoría.
    """

    sample = get_sample_row(session, "tendencias_por_categoria_fecha")

    if not sample:
        return {
            "query": "tendencias_por_categoria_fecha",
            "descripcion": "Top tendencias por categoría y fecha",
            "partition_key": None,
            "rows": []
        }

    rows = session.execute("""
                           SELECT categoria_id, fecha, score_tendencia, producto_id,
                                  total_eventos, total_vistas, total_clicks,
                                  total_busquedas, total_compras
                           FROM tendencias_por_categoria_fecha
                           WHERE categoria_id = %s
                             AND fecha = %s
                               LIMIT 10
                           """, (sample.categoria_id, sample.fecha))

    return {
        "query": "tendencias_por_categoria_fecha",
        "descripcion": "Top tendencias por categoría y fecha",
        "partition_key": {
            "categoria_id": sample.categoria_id,
            "fecha": serialize_value(sample.fecha)
        },
        "rows": [row_to_dict(row) for row in rows]
    }