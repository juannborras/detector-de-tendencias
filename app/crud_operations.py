from app.config import CASSANDRA_KEYSPACE
from app.connections import (
    get_cassandra_session,
    get_mongo_db,
    get_neo4j_driver,
    get_redis_client,
)
from app.models.redis_keys import TRENDING_GLOBAL_KEY
from app.queries.neo4j_queries import TIPOS_INTERACCION


def require_text(value, field_name):
    normalized = (value or "").strip()

    if not normalized:
        raise ValueError(f"{field_name} es obligatorio")

    return normalized


def parse_int(value, field_name):
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{field_name} debe ser entero") from error


def parse_float(value, field_name):
    try:
        return float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{field_name} debe ser numerico") from error


def parse_date(value, field_name):
    text = require_text(value, field_name)

    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError as error:
        raise ValueError(f"{field_name} debe tener formato YYYY-MM-DD") from error


def serialize_value(value):
    if value is None:
        return None

    if hasattr(value, "date") and callable(value.date):
        try:
            return value.date().isoformat()
        except Exception:
            pass

    if hasattr(value, "isoformat"):
        return value.isoformat()

    return value


def row_to_dict(row):
    if not row:
        return None

    return {
        key: serialize_value(value)
        for key, value in row._asdict().items()
    }


def operation_result(engine, operation, statement, params, verification, details=None):
    return {
        "status": "ok" if verification.get("verified") else "error",
        "engine": engine,
        "operation": operation,
        "statement": statement,
        "params": params,
        "verification": verification,
        "details": details or {},
    }


def mongo_upsert_product(producto_id, nombre, categoria_id, marca, precio, stock):
    client = None

    try:
        producto = {
            "producto_id": require_text(producto_id, "producto_id"),
            "nombre": require_text(nombre, "nombre"),
            "categoria_id": require_text(categoria_id, "categoria_id"),
            "marca": require_text(marca, "marca"),
            "precio": parse_float(precio, "precio"),
            "stock": parse_int(stock, "stock"),
            "fecha_alta": datetime.now().isoformat(),
        }

        client, db = get_mongo_db()
        result = db.productos.update_one(
            {"producto_id": producto["producto_id"]},
            {"$set": producto},
            upsert=True,
        )
        stored = db.productos.find_one(
            {"producto_id": producto["producto_id"]},
            {"_id": 0},
        )

        return operation_result(
            "MongoDB",
            "upsert_producto",
            "db.productos.update_one({'producto_id': producto_id}, {'$set': producto}, upsert=True)",
            producto,
            {
                "verified": stored is not None,
                "persisted": stored is not None,
                "read_back": stored,
            },
            {
                "matched_count": result.matched_count,
                "modified_count": result.modified_count,
                "upserted_id": str(result.upserted_id) if result.upserted_id else None,
            },
        )

    finally:
        if client:
            client.close()


def mongo_delete_product(producto_id):
    client = None

    try:
        normalized_id = require_text(producto_id, "producto_id")
        client, db = get_mongo_db()
        result = db.productos.delete_one({"producto_id": normalized_id})
        stored = db.productos.find_one(
            {"producto_id": normalized_id},
            {"_id": 0},
        )

        return operation_result(
            "MongoDB",
            "delete_producto",
            "db.productos.delete_one({'producto_id': producto_id})",
            {"producto_id": normalized_id},
            {
                "verified": stored is None,
                "deleted": stored is None,
                "read_back": stored,
            },
            {"deleted_count": result.deleted_count},
        )

    finally:
        if client:
            client.close()


def cassandra_upsert_daily_summary(
    fecha,
    producto_id,
    categoria_id,
    total_eventos,
    total_vistas,
    total_clicks,
    total_busquedas,
    total_favoritos,
    total_compras,
    score_tendencia,
):
    cluster = None

    try:
        parsed_fecha = parse_date(fecha, "fecha")
        params = {
            "fecha": parsed_fecha,
            "producto_id": require_text(producto_id, "producto_id"),
            "categoria_id": require_text(categoria_id, "categoria_id"),
            "total_eventos": parse_int(total_eventos, "total_eventos"),
            "total_vistas": parse_int(total_vistas, "total_vistas"),
            "total_clicks": parse_int(total_clicks, "total_clicks"),
            "total_busquedas": parse_int(total_busquedas, "total_busquedas"),
            "total_favoritos": parse_int(total_favoritos, "total_favoritos"),
            "total_compras": parse_int(total_compras, "total_compras"),
            "score_tendencia": parse_float(score_tendencia, "score_tendencia"),
        }

        cluster, session = get_cassandra_session()
        session.set_keyspace(CASSANDRA_KEYSPACE)
        session.execute(
            """
            INSERT INTO resumen_diario (
                fecha, producto_id, categoria_id, total_eventos,
                total_vistas, total_clicks, total_busquedas,
                total_favoritos, total_compras, score_tendencia
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                params["fecha"],
                params["producto_id"],
                params["categoria_id"],
                params["total_eventos"],
                params["total_vistas"],
                params["total_clicks"],
                params["total_busquedas"],
                params["total_favoritos"],
                params["total_compras"],
                params["score_tendencia"],
            ),
        )
        stored = session.execute(
            """
            SELECT fecha, producto_id, categoria_id, total_eventos,
                   total_vistas, total_clicks, total_busquedas,
                   total_favoritos, total_compras, score_tendencia
            FROM resumen_diario
            WHERE fecha = %s AND producto_id = %s
            """,
            (params["fecha"], params["producto_id"]),
        ).one()

        display_params = dict(params)
        display_params["fecha"] = serialize_value(display_params["fecha"])

        return operation_result(
            "Cassandra",
            "upsert_resumen_diario",
            "INSERT INTO resumen_diario (...) VALUES (...)",
            display_params,
            {
                "verified": stored is not None,
                "persisted": stored is not None,
                "read_back": row_to_dict(stored),
            },
        )

    finally:
        if cluster:
            cluster.shutdown()


def cassandra_delete_daily_summary(fecha, producto_id):
    cluster = None

    try:
        parsed_fecha = parse_date(fecha, "fecha")
        normalized_producto_id = require_text(producto_id, "producto_id")
        cluster, session = get_cassandra_session()
        session.set_keyspace(CASSANDRA_KEYSPACE)
        session.execute(
            """
            DELETE FROM resumen_diario
            WHERE fecha = %s AND producto_id = %s
            """,
            (parsed_fecha, normalized_producto_id),
        )
        stored = session.execute(
            """
            SELECT fecha, producto_id
            FROM resumen_diario
            WHERE fecha = %s AND producto_id = %s
            """,
            (parsed_fecha, normalized_producto_id),
        ).one()

        return operation_result(
            "Cassandra",
            "delete_resumen_diario",
            "DELETE FROM resumen_diario WHERE fecha = fecha AND producto_id = producto_id",
            {
                "fecha": serialize_value(parsed_fecha),
                "producto_id": normalized_producto_id,
            },
            {
                "verified": stored is None,
                "deleted": stored is None,
                "read_back": row_to_dict(stored),
            },
        )

    finally:
        if cluster:
            cluster.shutdown()


def redis_upsert_global_score(producto_id, score):
    normalized_producto_id = require_text(producto_id, "producto_id")
    parsed_score = parse_float(score, "score")
    redis_client = get_redis_client()
    redis_client.zadd(TRENDING_GLOBAL_KEY, {normalized_producto_id: parsed_score})
    stored_score = redis_client.zscore(TRENDING_GLOBAL_KEY, normalized_producto_id)

    return operation_result(
        "Redis",
        "upsert_ranking_global",
        f"ZADD {TRENDING_GLOBAL_KEY} score producto_id",
        {
            "key": TRENDING_GLOBAL_KEY,
            "producto_id": normalized_producto_id,
            "score": parsed_score,
        },
        {
            "verified": stored_score is not None,
            "persisted": stored_score is not None,
            "read_back": {
                "producto_id": normalized_producto_id,
                "score": stored_score,
            },
        },
    )


def redis_delete_global_score(producto_id):
    normalized_producto_id = require_text(producto_id, "producto_id")
    redis_client = get_redis_client()
    removed = redis_client.zrem(TRENDING_GLOBAL_KEY, normalized_producto_id)
    stored_score = redis_client.zscore(TRENDING_GLOBAL_KEY, normalized_producto_id)

    return operation_result(
        "Redis",
        "delete_ranking_global",
        f"ZREM {TRENDING_GLOBAL_KEY} producto_id",
        {
            "key": TRENDING_GLOBAL_KEY,
            "producto_id": normalized_producto_id,
        },
        {
            "verified": stored_score is None,
            "deleted": stored_score is None,
            "read_back": {
                "producto_id": normalized_producto_id,
                "score": stored_score,
            },
        },
        {"removed": removed},
    )


def neo4j_upsert_user_event(usuario_id, producto_id, tipo_evento):
    driver = None

    try:
        tipo_normalizado = normalize_event_type(tipo_evento, "tipo_evento")
        params = {
            "usuario_id": require_text(usuario_id, "usuario_id"),
            "producto_id": require_text(producto_id, "producto_id"),
        }
        cypher = f"""
        MERGE (u:Usuario {{usuario_id: $usuario_id}})
        MERGE (p:Producto {{producto_id: $producto_id}})
        MERGE (u)-[r:{tipo_normalizado}]->(p)
        ON CREATE SET r.cantidad = 1, r.fecha_ultima = datetime()
        ON MATCH SET r.cantidad = coalesce(r.cantidad, 0) + 1,
                      r.fecha_ultima = datetime()
        RETURN u.usuario_id AS usuario_id,
               p.producto_id AS producto_id,
               type(r) AS tipo_evento,
               r.cantidad AS cantidad,
               r.fecha_ultima AS fecha_ultima
        """
        driver = get_neo4j_driver()

        with driver.session() as session:
            record = session.run(cypher, **params).single()

        stored = dict(record) if record else None

        return operation_result(
            "Neo4j",
            "upsert_evento_usuario_producto",
            cypher.strip(),
            {
                **params,
                "tipo_evento": tipo_normalizado,
            },
            {
                "verified": stored is not None,
                "persisted": stored is not None,
                "read_back": stored,
            },
        )

    finally:
        if driver:
            driver.close()


def normalize_event_type(value, field_name):
    normalized = require_text(value, field_name).upper()

    if normalized not in TIPOS_INTERACCION:
        raise ValueError(
            f"{field_name} debe ser uno de: " + ", ".join(TIPOS_INTERACCION)
        )

    return normalized


def neo4j_delete_user_event(usuario_id, producto_id, tipo_evento):
    driver = None

    try:
        tipo_normalizado = normalize_event_type(tipo_evento, "tipo_evento")
        params = {
            "usuario_id": require_text(usuario_id, "usuario_id"),
            "producto_id": require_text(producto_id, "producto_id"),
        }
        cypher = f"""
        MATCH (u:Usuario {{usuario_id: $usuario_id}})
        MATCH (p:Producto {{producto_id: $producto_id}})
        MATCH (u)-[r:{tipo_normalizado}]->(p)
        DELETE r
        RETURN u.usuario_id AS usuario_id,
               p.producto_id AS producto_id,
               $tipo_evento AS tipo_evento,
               count(r) AS relaciones_eliminadas
        """
        verification_cypher = f"""
        MATCH (u:Usuario {{usuario_id: $usuario_id}})
        MATCH (p:Producto {{producto_id: $producto_id}})
        OPTIONAL MATCH (u)-[r:{tipo_normalizado}]->(p)
        RETURN count(r) AS relaciones_restantes
        """
        driver = get_neo4j_driver()

        with driver.session() as session:
            record = session.run(
                cypher,
                **params,
                tipo_evento=tipo_normalizado,
            ).single()
            verification = session.run(verification_cypher, **params).single()

        return operation_result(
            "Neo4j",
            "delete_evento_usuario_producto",
            cypher.strip(),
            {
                **params,
                "tipo_evento": tipo_normalizado,
            },
            {
                "verified": verification and verification["relaciones_restantes"] == 0,
                "deleted": verification and verification["relaciones_restantes"] == 0,
                "read_back": dict(record) if record else None,
            },
            {
                "relaciones_restantes": (
                    verification["relaciones_restantes"] if verification else None
                ),
            },
        )

    finally:
        if driver:
            driver.close()
