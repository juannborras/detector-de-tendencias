from datetime import datetime

from cassandra.util import Date

from app.config import (
    CASSANDRA_KEYSPACE,
    QUERY_FETCH_LIMIT,
    QUERY_SAMPLE_LIMIT,
    QUERY_TOP_LIMIT,
    TOTAL_EVENTOS,
)
from app.connections import get_cassandra_session

EVENT_TYPES = ["vista", "click", "busqueda", "favorito", "compra"]


def normalize_limit(limit):
    return max(1, int(limit))

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


def parse_fecha(fecha):
    """
    Normaliza una fecha recibida desde consola, dashboard o Cassandra.

    El dashboard trabaja con strings ISO como "2026-05-01", pero Cassandra
    consulta la partition key date con objetos fecha. Esta función permite usar
    la misma query desde ambos lugares.
    """

    if fecha is None:
        return None

    if isinstance(fecha, str):
        return datetime.strptime(fecha.strip(), "%Y-%m-%d").date()

    return fecha


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


def get_resumen_diario_fechas(session):
    """
    Devuelve las fechas que realmente existen en resumen_diario.

    Como resumen_diario se carga a partir de eventos reales, cada fecha devuelta
    tiene al menos un producto con eventos asociados.
    """

    rows = session.execute("""
                           SELECT DISTINCT fecha
                           FROM resumen_diario
                           """)

    return sorted({
        serialize_value(row.fecha)
        for row in rows
        if row.fecha is not None
    })


def select_dashboard_fecha(available_dates, requested_fecha=None):
    """
    Elige una fecha segura para dashboard.

    Si el usuario seleccionó una fecha que existe, se usa esa. Si no, se toma
    la fecha más reciente disponible.
    """

    if not available_dates:
        return None

    if requested_fecha in available_dates:
        return requested_fecha

    return available_dates[-1]


def get_eventos_por_tipo_for_dashboard(session, fecha=None):
    """
    Devuelve la cantidad de eventos por tipo para una fecha existente.

    Importante:
    No hacemos un GROUP BY libre como en SQL.
    En Cassandra consultamos respetando la partition key:
    tipo_evento + fecha.
    """

    parsed_fecha = parse_fecha(fecha)

    if not parsed_fecha:
        sample = get_sample_row(session, "eventos_por_tipo")

        if not sample:
            return []

        parsed_fecha = sample.fecha

    if not parsed_fecha:
        return []

    result = []

    for event_type in EVENT_TYPES:
        row = session.execute("""
                              SELECT COUNT(*) AS total
                              FROM eventos_por_tipo
                              WHERE tipo_evento = %s
                                AND fecha = %s
                              """, (event_type, parsed_fecha)).one()

        result.append({
            "tipo_evento": event_type,
            "fecha": serialize_value(parsed_fecha),
            "total": row.total
        })

    return result


def get_cassandra_dashboard_data(fecha=None):
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

        available_dates = get_resumen_diario_fechas(session)
        requested_fecha = serialize_value(parse_fecha(fecha)) if fecha else None
        selected_fecha = select_dashboard_fecha(available_dates, requested_fecha)

        resumen = query_resumen_diario(session, selected_fecha)
        tendencias = query_tendencias_por_categoria_fecha(session)
        tendencias_diarias = query_top_tendencias_resumen_diario(
            session,
            fecha=selected_fecha,
        )

        return {
            "status": "ok",
            "counts": counts,
            "selected_fecha": selected_fecha,
            "resumen_diario_fechas": available_dates,
            "eventos_por_tipo": get_eventos_por_tipo_for_dashboard(
                session,
                selected_fecha,
            ),
            "top_tendencias_categoria_fecha": tendencias["rows"],
            "top_tendencias_resumen_diario": tendencias_diarias["rows"],
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
            "selected_fecha": None,
            "resumen_diario_fechas": [],
            "eventos_por_tipo": [],
            "top_tendencias_categoria_fecha": [],
            "top_tendencias_resumen_diario": [],
            "resumen_diario_sample": []
        }

    finally:
        if cluster:
            cluster.shutdown()

def run_cassandra_queries():
    """
    Ejecuta las consultas Cassandra por consola.
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
            query_top_tendencias_resumen_diario(session),
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

def query_eventos_por_producto(session, limit=QUERY_SAMPLE_LIMIT):
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

    safe_limit = normalize_limit(limit)

    rows = session.execute(f"""
                           SELECT producto_id, fecha, timestamp, evento_id, usuario_id, tipo_evento, categoria_id
                           FROM eventos_por_producto
                           WHERE producto_id = %s
                             AND fecha = %s
                               LIMIT {safe_limit}
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


def query_eventos_por_usuario(session, limit=QUERY_SAMPLE_LIMIT):
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

    safe_limit = normalize_limit(limit)

    rows = session.execute(f"""
        SELECT usuario_id, fecha, timestamp, evento_id, producto_id, tipo_evento, categoria_id
        FROM eventos_por_usuario
        WHERE usuario_id = %s
          AND fecha = %s
        LIMIT {safe_limit}
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


def query_eventos_por_categoria(session, limit=QUERY_SAMPLE_LIMIT):
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

    safe_limit = normalize_limit(limit)

    rows = session.execute(f"""
        SELECT categoria_id, fecha, timestamp, evento_id, usuario_id, producto_id, tipo_evento
        FROM eventos_por_categoria
        WHERE categoria_id = %s
          AND fecha = %s
        LIMIT {safe_limit}
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



def query_eventos_por_tipo(session, limit=QUERY_SAMPLE_LIMIT):
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

    safe_limit = normalize_limit(limit)

    rows = session.execute(f"""
        SELECT tipo_evento, fecha, timestamp, evento_id, usuario_id, producto_id, categoria_id
        FROM eventos_por_tipo
        WHERE tipo_evento = %s
          AND fecha = %s
        LIMIT {safe_limit}
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



def query_resumen_diario(
    session,
    fecha=None,
    limit=QUERY_TOP_LIMIT,
    fetch_limit=QUERY_FETCH_LIMIT,
):
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

    parsed_fecha = parse_fecha(fecha)

    if not parsed_fecha:
        sample = get_sample_row(session, "resumen_diario")

        if sample:
            parsed_fecha = sample.fecha

    if not parsed_fecha:
        return {
            "query": "resumen_diario",
            "descripcion": "Resumen diario de productos",
            "partition_key": None,
            "rows": []
        }

    safe_limit = normalize_limit(limit)
    safe_fetch_limit = normalize_limit(fetch_limit)

    rows = session.execute(f"""
                           SELECT fecha, producto_id, categoria_id, total_eventos,
                                  total_vistas, total_clicks, total_busquedas,
                                  total_favoritos,
                                  total_compras, score_tendencia
                           FROM resumen_diario
                           WHERE fecha = %s
                           LIMIT {safe_fetch_limit}
                           """, (parsed_fecha,))

    sorted_rows = sorted(
        [row_to_dict(row) for row in rows],
        key=lambda row: (
            row.get("score_tendencia") or 0,
            row.get("total_eventos") or 0,
            row.get("producto_id") or ""
        ),
        reverse=True
    )

    return {
        "query": "resumen_diario",
        "descripcion": "Resumen diario de productos",
        "partition_key": {
            "fecha": serialize_value(parsed_fecha)
        },
        "rows": sorted_rows[:safe_limit]
    }

def query_tendencias_por_categoria_fecha(session, limit=QUERY_TOP_LIMIT):
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

    safe_limit = normalize_limit(limit)

    rows = session.execute(f"""
                           SELECT categoria_id, fecha, score_tendencia, producto_id,
                                  total_eventos, total_vistas, total_clicks,
                                  total_busquedas, total_favoritos, total_compras
                           FROM tendencias_por_categoria_fecha
                           WHERE categoria_id = %s
                             AND fecha = %s
                               LIMIT {safe_limit}
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


def query_top_tendencias_resumen_diario(
    session,
    fecha=None,
    limit=QUERY_TOP_LIMIT,
    fetch_limit=QUERY_FETCH_LIMIT,
):
    """
    Consulta 7:
    obtiene los productos con mayor score dentro de una fecha real.

    Tabla usada:
    resumen_diario

    Partition key:
    fecha

    Funcionamiento:
    Esta consulta usa los resumenes diarios como fuente de verdad para detectar
    tendencias. Primero toma una fecha existente, luego trae los productos de
    esa fecha y ordena en Python por score_tendencia descendente.

    Nota:
    Para un sistema productivo con muchos datos, convendria crear una tabla
    especifica modelada por esta consulta, por ejemplo tendencias_por_fecha.
    Para el TPI, con dataset chico, esta adaptacion es clara para explicar el
    detector sin agregar otra tabla fisica.
    """

    parsed_fecha = parse_fecha(fecha)

    if not parsed_fecha:
        sample = get_sample_row(session, "resumen_diario")

        if sample:
            parsed_fecha = sample.fecha

    if not parsed_fecha:
        return {
            "query": "resumen_diario",
            "descripcion": "Top diario de productos tendencia",
            "partition_key": None,
            "rows": []
        }

    safe_limit = normalize_limit(limit)
    safe_fetch_limit = normalize_limit(fetch_limit)

    rows = session.execute(f"""
                           SELECT fecha, producto_id, categoria_id, total_eventos,
                                  total_vistas, total_clicks, total_busquedas,
                                  total_favoritos, total_compras, score_tendencia
                           FROM resumen_diario
                           WHERE fecha = %s
                           LIMIT {safe_fetch_limit}
                           """, (parsed_fecha,))

    sorted_rows = sorted(
        [row_to_dict(row) for row in rows],
        key=lambda row: (
            row.get("score_tendencia") or 0,
            row.get("total_eventos") or 0,
            row.get("producto_id") or ""
        ),
        reverse=True
    )

    return {
        "query": "resumen_diario",
        "descripcion": "Top diario de productos tendencia",
        "partition_key": {
            "fecha": serialize_value(parsed_fecha)
        },
        "rows": sorted_rows[:safe_limit]
    }
