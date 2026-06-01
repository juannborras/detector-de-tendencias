from app.connections import get_neo4j_driver
from app.config import NEO4J_DEFAULT_EVENT_TYPE, QUERY_TOP_LIMIT


TIPOS_INTERACCION = ["VIO", "CLICK", "BUSCO", "FAVORITO", "COMPRO"]


COUNTS_CYPHER = """
WITH $tipos AS tipos
MATCH (u:Usuario)
WITH tipos, count(u) AS usuarios
MATCH (p:Producto)
WITH tipos, usuarios, count(p) AS productos
MATCH (c:Categoria)
WITH tipos, usuarios, productos, count(c) AS categorias
CALL {
    WITH tipos
    MATCH (:Usuario)-[r]->(:Producto)
    WHERE type(r) IN tipos
    RETURN
        count(r) AS relaciones_interaccion,
        coalesce(sum(r.cantidad), 0) AS eventos_representados
}
RETURN
    usuarios,
    productos,
    categorias,
    relaciones_interaccion,
    eventos_representados
"""

RELACIONES_POR_TIPO_CYPHER = """
MATCH (:Usuario)-[r]->(:Producto)
WHERE type(r) IN $tipos
RETURN
    type(r) AS tipo,
    count(r) AS total_relaciones,
    coalesce(sum(r.cantidad), 0) AS total_eventos
ORDER BY total_eventos DESC
"""

USUARIOS_MAS_ACTIVOS_CYPHER = """
MATCH (u:Usuario)-[r]->(:Producto)
WHERE type(r) IN $tipos
RETURN
    u.usuario_id AS usuario_id,
    u.nombre AS nombre,
    coalesce(sum(r.cantidad), 0) AS eventos
ORDER BY eventos DESC
LIMIT $limit
"""

PRODUCTOS_MAS_CONECTADOS_CYPHER = """
MATCH (:Usuario)-[r]->(p:Producto)
WHERE type(r) = $tipo
RETURN
    p.producto_id AS producto_id,
    p.nombre AS nombre,
    coalesce(sum(r.cantidad), 0) AS interacciones
ORDER BY interacciones DESC
LIMIT $limit
"""

RECOMENDACIONES_SAMPLE_CYPHER = """
MATCH (u:Usuario)-[:INTERESADO_EN]->(c:Categoria)
MATCH (p:Producto)-[:PERTENECE_A]->(c)
WHERE NOT EXISTS {
    MATCH (u)-[r]->(p)
    WHERE type(r) IN $tipos
}
RETURN
    u.usuario_id AS usuario_id,
    p.producto_id AS producto_recomendado,
    "Categoria de interes compartida" AS motivo
LIMIT $limit
"""


def format_cypher(cypher):
    """
    Normaliza el Cypher para mostrarlo por consola sin perder legibilidad.
    """

    return "\n".join(
        line.rstrip()
        for line in cypher.strip().splitlines()
    )


def build_query_result(query, descripcion, cypher, params, rows, extra=None):
    """
    Devuelve una salida comun para consola, dashboard y documentacion.
    """

    result = {
        "query": query,
        "descripcion": descripcion,
        "cypher": format_cypher(cypher),
        "params": params,
        "rows": rows,
    }

    if extra:
        result.update(extra)

    return result


def query_counts(session):
    """
    Consulta cantidades principales de nodos, relaciones y eventos.
    """

    params = {"tipos": TIPOS_INTERACCION}
    record = session.run(COUNTS_CYPHER, **params).single()
    counts = {
        "usuarios": record["usuarios"],
        "productos": record["productos"],
        "categorias": record["categorias"],
        "relaciones_interaccion": record["relaciones_interaccion"],
        "eventos_representados": record["eventos_representados"],
    }

    return build_query_result(
        "conteo_grafo",
        "Conteo de nodos, relaciones y eventos representados",
        COUNTS_CYPHER,
        params,
        [counts],
        {"counts": counts},
    )


def query_relaciones_por_tipo(session):
    """
    Consulta cuantas relaciones y eventos hay por tipo de interaccion.
    """

    params = {"tipos": TIPOS_INTERACCION}
    rows = [
        {
            "tipo": record["tipo"],
            "total_relaciones": record["total_relaciones"],
            "total_eventos": record["total_eventos"],
        }
        for record in session.run(RELACIONES_POR_TIPO_CYPHER, **params)
    ]

    return build_query_result(
        "relaciones_por_tipo",
        "Relaciones y eventos agrupados por tipo",
        RELACIONES_POR_TIPO_CYPHER,
        params,
        rows,
    )


def query_usuarios_mas_activos(session, limit=QUERY_TOP_LIMIT):
    """
    Consulta usuarios con mayor cantidad de eventos/interacciones.
    """

    params = {
        "tipos": TIPOS_INTERACCION,
        "limit": limit,
    }
    rows = [
        {
            "usuario_id": record["usuario_id"],
            "nombre": record["nombre"],
            "eventos": record["eventos"],
        }
        for record in session.run(USUARIOS_MAS_ACTIVOS_CYPHER, **params)
    ]

    return build_query_result(
        "usuarios_mas_activos",
        "Usuarios con mayor actividad",
        USUARIOS_MAS_ACTIVOS_CYPHER,
        params,
        rows,
    )


def query_productos_mas_conectados(
    session,
    tipo_evento=NEO4J_DEFAULT_EVENT_TYPE,
    limit=QUERY_TOP_LIMIT,
):
    """
    Consulta productos con mayor cantidad de interacciones por tipo.
    """

    params = {
        "tipo": normalize_event_type(tipo_evento),
        "limit": limit,
    }
    rows = [
        {
            "producto_id": record["producto_id"],
            "nombre": record["nombre"],
            "interacciones": record["interacciones"],
        }
        for record in session.run(PRODUCTOS_MAS_CONECTADOS_CYPHER, **params)
    ]

    return build_query_result(
        "productos_mas_conectados",
        "Productos con mas interacciones por tipo de evento",
        PRODUCTOS_MAS_CONECTADOS_CYPHER,
        params,
        rows,
    )


def query_recomendaciones_sample(session, limit=QUERY_TOP_LIMIT):
    """
    Consulta una muestra de recomendaciones por categoria de interes.
    """

    params = {
        "tipos": TIPOS_INTERACCION,
        "limit": limit,
    }
    rows = [
        {
            "usuario_id": record["usuario_id"],
            "producto_recomendado": record["producto_recomendado"],
            "motivo": record["motivo"],
        }
        for record in session.run(RECOMENDACIONES_SAMPLE_CYPHER, **params)
    ]

    return build_query_result(
        "recomendaciones_sample",
        "Productos recomendados por categoria de interes compartida",
        RECOMENDACIONES_SAMPLE_CYPHER,
        params,
        rows,
    )


def normalize_event_type(tipo_evento):
    normalized = (tipo_evento or "").strip().upper()

    if normalized not in TIPOS_INTERACCION:
        raise ValueError(
            "tipo_evento invalido. Usar uno de: "
            + ", ".join(TIPOS_INTERACCION)
        )

    return normalized


def execute_neo4j_queries(session, tipo_evento=NEO4J_DEFAULT_EVENT_TYPE):
    """
    Lista unica de consultas Neo4j de demostracion.
    """

    return [
        query_counts(session),
        query_relaciones_por_tipo(session),
        query_usuarios_mas_activos(session),
        query_productos_mas_conectados(session, tipo_evento=tipo_evento),
        query_recomendaciones_sample(session),
    ]


def print_query_result(query):
    print()
    print(query["descripcion"])
    print("-" * 60)
    print("Cypher:")
    print(query["cypher"])

    if query.get("params"):
        print(f"Parametros: {query['params']}")

    print(f"Filas devueltas: {len(query['rows'])}")

    for row in query["rows"][:5]:
        print(row)


def run_neo4j_queries(show_output=True, tipo_evento=NEO4J_DEFAULT_EVENT_TYPE):
    """
    Ejecuta todas las consultas Neo4j por consola.

    El dashboard reutiliza esta funcion con show_output=False para consumir los
    mismos resultados sin duplicar el listado de consultas.
    """

    driver = None

    try:
        driver = get_neo4j_driver()

        with driver.session() as session:
            queries = execute_neo4j_queries(session, tipo_evento=tipo_evento)

        if show_output:
            print("Neo4j queries")
            print("=" * 60)

            for query in queries:
                print_query_result(query)

        return queries

    except Exception as error:
        if show_output:
            print("Neo4j queries ERROR")
            print(error)
            return []

        raise

    finally:
        if driver:
            driver.close()


def query_map(queries):
    return {
        query["query"]: query
        for query in queries
    }


def build_neo4j_dashboard_data(queries):
    """
    Adapta la salida de run_neo4j_queries al contrato del dashboard.
    """

    queries_by_name = query_map(queries)

    return {
        "status": "ok",
        "counts": queries_by_name["conteo_grafo"]["counts"],
        "relaciones_por_tipo": queries_by_name["relaciones_por_tipo"]["rows"],
        "usuarios_mas_activos": queries_by_name["usuarios_mas_activos"]["rows"],
        "productos_mas_conectados": queries_by_name["productos_mas_conectados"]["rows"],
        "recomendaciones_sample": queries_by_name["recomendaciones_sample"]["rows"],
        "queries": [
            {
                "query": query["query"],
                "descripcion": query["descripcion"],
                "cypher": query["cypher"],
                "params": query["params"],
            }
            for query in queries
        ],
    }


def get_error_response(error):
    """
    Devuelve la estructura esperada cuando ocurre un error.
    """

    return {
        "status": "error",
        "message": f"Error al obtener datos de Neo4j: {error}",
        "counts": {
            "usuarios": 0,
            "productos": 0,
            "categorias": 0,
            "relaciones_interaccion": 0,
            "eventos_representados": 0,
        },
        "relaciones_por_tipo": [],
        "usuarios_mas_activos": [],
        "productos_mas_conectados": [],
        "recomendaciones_sample": [],
        "queries": [],
    }


def get_neo4j_dashboard_data():
    """
    Devuelve datos de Neo4j para el dashboard.

    No define ni enumera consultas propias: reutiliza run_neo4j_queries para
    que exista un unico punto donde se decide que consultas Neo4j se ejecutan.
    """

    try:
        return build_neo4j_dashboard_data(
            run_neo4j_queries(show_output=False)
        )

    except Exception as error:
        return get_error_response(error)
