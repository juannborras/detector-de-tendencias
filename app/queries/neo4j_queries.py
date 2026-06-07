from app.config import (
    NEO4J_DEFAULT_EVENT_TYPE,
    QUERY_LOOKUP_LIMIT,
    QUERY_SAMPLE_LIMIT,
    QUERY_TOP_LIMIT,
)
from app.connections import get_neo4j_driver


TIPOS_INTERACCION = ["VIO", "CLICK", "BUSCO", "FAVORITO", "COMPRO"]

EVENT_TYPE_ALIASES = {
    "VIO": "VIO",
    "VISTA": "VIO",
    "VISTAS": "VIO",
    "VER": "VIO",
    "CLICK": "CLICK",
    "CLICKS": "CLICK",
    "BUSCO": "BUSCO",
    "BUSQUEDA": "BUSCO",
    "BUSQUEDAS": "BUSCO",
    "BUSCAR": "BUSCO",
    "FAVORITO": "FAVORITO",
    "FAVORITOS": "FAVORITO",
    "FAV": "FAVORITO",
    "COMPRO": "COMPRO",
    "COMPRA": "COMPRO",
    "COMPRAS": "COMPRO",
    "COMPRAR": "COMPRO",
}


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

PRODUCTOS_POR_EVENTO_CYPHER = """
MATCH (:Usuario)-[r]->(p:Producto)
WHERE type(r) = $tipo_evento
RETURN
    p.producto_id AS producto_id,
    p.nombre AS nombre,
    $tipo_evento AS tipo_evento,
    count(r) AS usuarios_distintos,
    coalesce(sum(r.cantidad), 0) AS total_eventos
ORDER BY total_eventos DESC, usuarios_distintos DESC, producto_id ASC
LIMIT $limit
"""

CATEGORIAS_CON_MAS_INTERES_CYPHER = """
MATCH (u:Usuario)-[r:INTERESADO_EN]->(c:Categoria)
RETURN
    c.categoria_id AS categoria_id,
    c.nombre AS categoria,
    count(DISTINCT u) AS usuarios_interesados,
    coalesce(sum(r.cantidad), 0) AS eventos_interes
ORDER BY eventos_interes DESC, usuarios_interesados DESC, categoria_id ASC
LIMIT $limit
"""

USUARIOS_POR_PRODUCTO_EVENTO_CYPHER = """
MATCH (u:Usuario)-[r]->(p:Producto {producto_id: $producto_id})
WHERE type(r) = $tipo_evento
RETURN
    u.usuario_id AS usuario_id,
    u.nombre AS nombre,
    p.producto_id AS producto_id,
    p.nombre AS producto,
    $tipo_evento AS tipo_evento,
    coalesce(r.cantidad, 0) AS cantidad,
    r.ultimo_evento AS ultimo_evento
ORDER BY cantidad DESC, usuario_id ASC
LIMIT $limit
"""

SAMPLE_PRODUCT_FOR_EVENT_CYPHER = """
MATCH (:Usuario)-[r]->(p:Producto)
WHERE type(r) = $tipo_evento
RETURN p.producto_id AS producto_id, coalesce(sum(r.cantidad), 0) AS total_eventos
ORDER BY total_eventos DESC, producto_id ASC
LIMIT $limit
"""

RECOMENDACIONES_SAMPLE_CYPHER = """
MATCH (u:Usuario)-[interes:INTERESADO_EN]->(c:Categoria)
MATCH (p:Producto)-[:PERTENECE_A]->(c)
WHERE NOT EXISTS {
    MATCH (u)-[r]->(p)
    WHERE type(r) IN $tipos
}
WITH
    u,
    c,
    p,
    coalesce(interes.cantidad, 0) AS afinidad_categoria
OPTIONAL MATCH (:Usuario)-[popularidad]->(p)
WHERE type(popularidad) IN $tipos
WITH
    u,
    c,
    p,
    afinidad_categoria,
    coalesce(sum(popularidad.cantidad), 0) AS popularidad_producto
RETURN
    u.usuario_id AS usuario_id,
    u.nombre AS usuario,
    c.categoria_id AS categoria_id,
    c.nombre AS categoria,
    p.producto_id AS producto_recomendado,
    p.nombre AS producto,
    "Categoria de interes compartida y producto no interactuado" AS motivo,
    afinidad_categoria,
    popularidad_producto
ORDER BY afinidad_categoria DESC, popularidad_producto DESC, usuario_id ASC
LIMIT $limit
"""


def normalize_event_type(tipo_evento=None):
    candidate = (tipo_evento or NEO4J_DEFAULT_EVENT_TYPE).strip().upper()
    normalized = EVENT_TYPE_ALIASES.get(candidate)

    if not normalized:
        raise ValueError(
            "tipo_evento invalido. Usar uno de: "
            + ", ".join(TIPOS_INTERACCION)
        )

    return normalized


def format_cypher(cypher):
    return "\n".join(
        line.rstrip()
        for line in cypher.strip().splitlines()
    )


def build_query_result(query, descripcion, cypher, params, rows, extra=None):
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


def record_to_dict(record):
    row = dict(record)

    if row.get("ultimo_evento") is not None:
        row["ultimo_evento"] = str(row["ultimo_evento"])

    return row


def query_counts(session):
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


def query_usuarios_mas_activos(session, limit=QUERY_TOP_LIMIT):
    params = {
        "tipos": TIPOS_INTERACCION,
        "limit": limit,
    }
    rows = [
        record_to_dict(record)
        for record in session.run(USUARIOS_MAS_ACTIVOS_CYPHER, **params)
    ]

    return build_query_result(
        "usuarios_mas_activos",
        "Usuarios con mayor actividad total en el grafo",
        USUARIOS_MAS_ACTIVOS_CYPHER,
        params,
        rows,
    )


def query_productos_mas_conectados(
    session,
    tipo_evento=NEO4J_DEFAULT_EVENT_TYPE,
    limit=QUERY_TOP_LIMIT,
):
    normalized_type = normalize_event_type(tipo_evento)
    params = {
        "tipo_evento": normalized_type,
        "limit": limit,
    }
    rows = [
        record_to_dict(record)
        for record in session.run(PRODUCTOS_POR_EVENTO_CYPHER, **params)
    ]

    return build_query_result(
        "productos_por_evento",
        "Productos con mas eventos del tipo elegido",
        PRODUCTOS_POR_EVENTO_CYPHER,
        params,
        rows,
        {"tipo_evento": normalized_type},
    )


def query_categorias_con_mas_interes(session, limit=QUERY_TOP_LIMIT):
    params = {"limit": limit}
    rows = [
        record_to_dict(record)
        for record in session.run(CATEGORIAS_CON_MAS_INTERES_CYPHER, **params)
    ]

    return build_query_result(
        "categorias_con_mas_interes",
        "Categorias con mas usuarios interesados",
        CATEGORIAS_CON_MAS_INTERES_CYPHER,
        params,
        rows,
    )


def get_sample_product_for_event(session, tipo_evento, limit=QUERY_LOOKUP_LIMIT):
    record = session.run(
        SAMPLE_PRODUCT_FOR_EVENT_CYPHER,
        tipo_evento=tipo_evento,
        limit=limit,
    ).single()

    if not record:
        return None

    return record["producto_id"]


def query_usuarios_por_producto_evento(
    session,
    producto_id=None,
    tipo_evento=NEO4J_DEFAULT_EVENT_TYPE,
    limit=QUERY_TOP_LIMIT,
):
    normalized_type = normalize_event_type(tipo_evento)
    selected_producto_id = (producto_id or "").strip()

    if not selected_producto_id:
        selected_producto_id = get_sample_product_for_event(session, normalized_type)

    if not selected_producto_id:
        return build_query_result(
            "usuarios_por_producto_evento",
            "Usuarios que realizaron el evento elegido sobre un producto",
            USUARIOS_POR_PRODUCTO_EVENTO_CYPHER,
            {
                "producto_id": None,
                "tipo_evento": normalized_type,
                "limit": limit,
            },
            [],
            {
                "producto_id": None,
                "tipo_evento": normalized_type,
            },
        )

    params = {
        "producto_id": selected_producto_id,
        "tipo_evento": normalized_type,
        "limit": limit,
    }
    rows = [
        record_to_dict(record)
        for record in session.run(USUARIOS_POR_PRODUCTO_EVENTO_CYPHER, **params)
    ]

    return build_query_result(
        "usuarios_por_producto_evento",
        "Usuarios que realizaron el evento elegido sobre un producto",
        USUARIOS_POR_PRODUCTO_EVENTO_CYPHER,
        params,
        rows,
        {
            "producto_id": selected_producto_id,
            "tipo_evento": normalized_type,
        },
    )


def query_recomendaciones_sample(session, limit=QUERY_TOP_LIMIT):
    params = {
        "tipos": TIPOS_INTERACCION,
        "limit": limit,
    }
    rows = [
        record_to_dict(record)
        for record in session.run(RECOMENDACIONES_SAMPLE_CYPHER, **params)
    ]

    return build_query_result(
        "recomendaciones_sample",
        "Recomendaciones por categoria de interes y popularidad del producto",
        RECOMENDACIONES_SAMPLE_CYPHER,
        params,
        rows,
    )


def execute_neo4j_queries(
    session,
    tipo_evento=NEO4J_DEFAULT_EVENT_TYPE,
    producto_id=None,
    producto_evento=None,
):
    selected_event = normalize_event_type(tipo_evento)
    selected_product_event = normalize_event_type(producto_evento or selected_event)

    return [
        query_counts(session),
        query_usuarios_mas_activos(session),
        query_productos_mas_conectados(session, tipo_evento=selected_event),
        query_categorias_con_mas_interes(session),
        query_usuarios_por_producto_evento(
            session,
            producto_id=producto_id,
            tipo_evento=selected_product_event,
        ),
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

    for row in query["rows"][:QUERY_SAMPLE_LIMIT]:
        print(row)


def run_neo4j_queries(
    show_output=True,
    tipo_evento=NEO4J_DEFAULT_EVENT_TYPE,
    producto_id=None,
    producto_evento=None,
):
    driver = None

    try:
        driver = get_neo4j_driver()

        with driver.session() as session:
            queries = execute_neo4j_queries(
                session,
                tipo_evento=tipo_evento,
                producto_id=producto_id,
                producto_evento=producto_evento,
            )

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
    queries_by_name = query_map(queries)
    productos_query = queries_by_name["productos_por_evento"]
    usuarios_producto_query = queries_by_name["usuarios_por_producto_evento"]

    return {
        "status": "ok",
        "counts": queries_by_name["conteo_grafo"]["counts"],
        "usuarios_mas_activos": queries_by_name["usuarios_mas_activos"]["rows"],
        "productos_por_evento": productos_query["rows"],
        "productos_mas_conectados": productos_query["rows"],
        "selected_tipo_evento": productos_query["tipo_evento"],
        "categorias_con_mas_interes": queries_by_name["categorias_con_mas_interes"]["rows"],
        "usuarios_por_producto_evento": usuarios_producto_query["rows"],
        "usuarios_producto_evento_context": {
            "producto_id": usuarios_producto_query.get("producto_id"),
            "tipo_evento": usuarios_producto_query.get("tipo_evento"),
        },
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
        "usuarios_mas_activos": [],
        "productos_por_evento": [],
        "productos_mas_conectados": [],
        "categorias_con_mas_interes": [],
        "usuarios_por_producto_evento": [],
        "usuarios_producto_evento_context": {},
        "recomendaciones_sample": [],
        "queries": [],
    }


def get_neo4j_dashboard_data(
    tipo_evento=NEO4J_DEFAULT_EVENT_TYPE,
    producto_id=None,
    producto_evento=None,
):
    try:
        return build_neo4j_dashboard_data(
            run_neo4j_queries(
                show_output=False,
                tipo_evento=tipo_evento,
                producto_id=producto_id,
                producto_evento=producto_evento,
            )
        )

    except Exception as error:
        return get_error_response(error)
