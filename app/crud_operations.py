import json
import re
from datetime import datetime

from app.config import CASSANDRA_KEYSPACE, QUERY_TOP_LIMIT
from app.connections import (
    get_cassandra_session,
    get_mongo_db,
    get_neo4j_driver,
    get_redis_client,
)
from app.models.redis_keys import (
    CACHE_TOP10_GLOBAL_KEY,
    TRENDING_CATEGORY_PREFIX,
    TRENDING_GLOBAL_KEY,
)
from app.queries.neo4j_queries import EVENT_TYPE_ALIASES, TIPOS_INTERACCION


def require_text(value, field_name):
    normalized = (value or "").strip()

    if not normalized:
        raise ValueError(f"{field_name} es obligatorio")

    return normalized


def canonical_identifier(value):
    return re.sub(r"\s+", "", str(value or ""))


def require_identifier(value, field_name):
    normalized = canonical_identifier(require_text(value, field_name))

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


def cassandra_tendencia_key(row):
    return (
        row.get("categoria_id"),
        row.get("fecha"),
        row.get("score_tendencia"),
        row.get("producto_id"),
    )


def find_cassandra_summary_rows(session, fecha, producto_id):
    target_producto_id = canonical_identifier(producto_id)
    rows = session.execute(
        """
        SELECT fecha, producto_id, categoria_id, total_eventos,
               total_vistas, total_clicks, total_busquedas,
               total_favoritos, total_compras, score_tendencia
        FROM resumen_diario
        WHERE fecha = %s
        """,
        (fecha,),
    )

    return [
        row
        for row in rows
        if canonical_identifier(row.producto_id) == target_producto_id
    ]


def find_cassandra_tendency_rows(session, fecha, producto_id, known_summary=None):
    rows_by_key = {}

    if known_summary:
        summaries = (
            known_summary
            if isinstance(known_summary, list)
            else [known_summary]
        )

        for summary_row in summaries:
            summary = row_to_dict(summary_row)
            rows_by_key[cassandra_tendencia_key(summary)] = summary

    filtered_rows = session.execute(
        """
        SELECT categoria_id, fecha, score_tendencia, producto_id
        FROM tendencias_por_categoria_fecha
        WHERE fecha = %s
        ALLOW FILTERING
        """,
        (fecha,),
    )
    target_producto_id = canonical_identifier(producto_id)

    for row in filtered_rows:
        row_dict = row_to_dict(row)

        if canonical_identifier(row_dict.get("producto_id")) == target_producto_id:
            rows_by_key[cassandra_tendencia_key(row_dict)] = row_dict

    return [
        row
        for row in rows_by_key.values()
        if all(value is not None for value in cassandra_tendencia_key(row))
    ]


def delete_cassandra_tendency_rows(session, rows):
    deleted = 0

    for row in rows:
        session.execute(
            """
            DELETE FROM tendencias_por_categoria_fecha
            WHERE categoria_id = %s
              AND fecha = %s
              AND score_tendencia = %s
              AND producto_id = %s
            """,
            (
                row["categoria_id"],
                row["fecha"],
                row["score_tendencia"],
                row["producto_id"],
            ),
        )
        deleted += 1

    return deleted


def delete_cassandra_summary_rows(session, rows):
    deleted = 0

    for row in rows:
        session.execute(
            """
            DELETE FROM resumen_diario
            WHERE fecha = %s AND producto_id = %s
            """,
            (row.fecha, row.producto_id),
        )
        deleted += 1

    return deleted


def resolve_redis_category_id(producto_id, categoria_id=None):
    normalized_categoria_id = canonical_identifier(categoria_id)

    if normalized_categoria_id:
        return normalized_categoria_id, "input"

    client = None

    try:
        client, db = get_mongo_db()
        product = db.productos.find_one(
            {"producto_id": producto_id},
            {"_id": 0, "categoria_id": 1},
        )

        if product and product.get("categoria_id"):
            return product["categoria_id"], "mongo_productos"

    finally:
        if client:
            client.close()

    return None, "sin_categoria"


def remove_product_from_category_rankings(redis_client, producto_id, keep_key=None):
    removed = 0

    for key in redis_client.scan_iter(match=f"{TRENDING_CATEGORY_PREFIX}*"):
        if key == keep_key:
            continue

        removed += redis_client.zrem(key, producto_id)

    return removed


def refresh_redis_top_cache(redis_client):
    top_global = redis_client.zrevrange(
        TRENDING_GLOBAL_KEY,
        0,
        QUERY_TOP_LIMIT - 1,
        withscores=True,
    )
    payload = [[producto_id, score] for producto_id, score in top_global]
    redis_client.setex(CACHE_TOP10_GLOBAL_KEY, 3600, json.dumps(payload))

    return [
        {
            "producto_id": producto_id,
            "score": score,
        }
        for producto_id, score in top_global
    ]


def mongo_upsert_product(producto_id, nombre, categoria_id, marca, precio, stock):
    client = None

    try:
        producto = {
            "producto_id": require_identifier(producto_id, "producto_id"),
            "nombre": require_text(nombre, "nombre"),
            "categoria_id": require_identifier(categoria_id, "categoria_id"),
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
        normalized_id = require_identifier(producto_id, "producto_id")
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
            "producto_id": require_identifier(producto_id, "producto_id"),
            "categoria_id": require_identifier(categoria_id, "categoria_id"),
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
        previous_summary_rows = find_cassandra_summary_rows(
            session,
            params["fecha"],
            params["producto_id"],
        )
        previous_tendency_rows = find_cassandra_tendency_rows(
            session,
            params["fecha"],
            params["producto_id"],
            previous_summary_rows,
        )
        deleted_previous_summaries = delete_cassandra_summary_rows(
            session,
            previous_summary_rows,
        )
        deleted_previous_tendencies = delete_cassandra_tendency_rows(
            session,
            previous_tendency_rows,
        )

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
        session.execute(
            """
            INSERT INTO tendencias_por_categoria_fecha (
                categoria_id, fecha, score_tendencia, producto_id,
                total_eventos, total_vistas, total_clicks,
                total_busquedas, total_favoritos, total_compras
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                params["categoria_id"],
                params["fecha"],
                params["score_tendencia"],
                params["producto_id"],
                params["total_eventos"],
                params["total_vistas"],
                params["total_clicks"],
                params["total_busquedas"],
                params["total_favoritos"],
                params["total_compras"],
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
        stored_tendency = session.execute(
            """
            SELECT categoria_id, fecha, score_tendencia, producto_id
            FROM tendencias_por_categoria_fecha
            WHERE categoria_id = %s
              AND fecha = %s
              AND score_tendencia = %s
              AND producto_id = %s
            """,
            (
                params["categoria_id"],
                params["fecha"],
                params["score_tendencia"],
                params["producto_id"],
            ),
        ).one()

        display_params = dict(params)
        display_params["fecha"] = serialize_value(display_params["fecha"])

        return operation_result(
            "Cassandra",
            "upsert_resumen_y_tendencia",
            "INSERT INTO resumen_diario (...) VALUES (...); INSERT INTO tendencias_por_categoria_fecha (...) VALUES (...)",
            display_params,
            {
                "verified": stored is not None and stored_tendency is not None,
                "persisted": stored is not None and stored_tendency is not None,
                "read_back_resumen": row_to_dict(stored),
                "read_back_tendencia": row_to_dict(stored_tendency),
            },
            {
                "deleted_previous_summaries": deleted_previous_summaries,
                "deleted_previous_tendencies": deleted_previous_tendencies,
                "previous_summaries": [
                    row_to_dict(row)
                    for row in previous_summary_rows
                ],
            },
        )

    finally:
        if cluster:
            cluster.shutdown()


def cassandra_delete_daily_summary(fecha, producto_id):
    cluster = None

    try:
        parsed_fecha = parse_date(fecha, "fecha")
        normalized_producto_id = require_identifier(producto_id, "producto_id")
        cluster, session = get_cassandra_session()
        session.set_keyspace(CASSANDRA_KEYSPACE)
        previous_summary_rows = find_cassandra_summary_rows(
            session,
            parsed_fecha,
            normalized_producto_id,
        )
        previous_tendency_rows = find_cassandra_tendency_rows(
            session,
            parsed_fecha,
            normalized_producto_id,
            previous_summary_rows,
        )

        deleted_summaries = delete_cassandra_summary_rows(
            session,
            previous_summary_rows,
        )
        deleted_tendencies = delete_cassandra_tendency_rows(
            session,
            previous_tendency_rows,
        )
        stored_rows = find_cassandra_summary_rows(
            session,
            parsed_fecha,
            normalized_producto_id,
        )
        remaining_tendencies = find_cassandra_tendency_rows(
            session,
            parsed_fecha,
            normalized_producto_id,
        )

        return operation_result(
            "Cassandra",
            "delete_resumen_y_tendencia",
            "DELETE FROM resumen_diario WHERE fecha = fecha AND producto_id = producto_id; DELETE FROM tendencias_por_categoria_fecha WHERE categoria_id = categoria_id AND fecha = fecha AND score_tendencia = score_tendencia AND producto_id = producto_id",
            {
                "fecha": serialize_value(parsed_fecha),
                "producto_id": normalized_producto_id,
            },
            {
                "verified": not stored_rows and not remaining_tendencies,
                "deleted": not stored_rows and not remaining_tendencies,
                "read_back_resumen": [
                    row_to_dict(row)
                    for row in stored_rows
                ],
                "remaining_tendencies": remaining_tendencies,
            },
            {
                "deleted_summaries": deleted_summaries,
                "deleted_tendencies": deleted_tendencies,
                "previous_summaries": [
                    row_to_dict(row)
                    for row in previous_summary_rows
                ],
                "previous_tendencies": previous_tendency_rows,
            },
        )

    finally:
        if cluster:
            cluster.shutdown()


def redis_upsert_global_score(producto_id, score, categoria_id=None):
    normalized_producto_id = require_identifier(producto_id, "producto_id")
    parsed_score = parse_float(score, "score")
    resolved_categoria_id, category_source = resolve_redis_category_id(
        normalized_producto_id,
        categoria_id,
    )

    if not resolved_categoria_id:
        raise ValueError(
            "categoria_id es obligatorio si el producto no existe en MongoDB"
        )

    redis_client = get_redis_client()
    category_key = f"{TRENDING_CATEGORY_PREFIX}{resolved_categoria_id}"

    redis_client.zadd(TRENDING_GLOBAL_KEY, {normalized_producto_id: parsed_score})
    removed_from_other_categories = remove_product_from_category_rankings(
        redis_client,
        normalized_producto_id,
        keep_key=category_key,
    )

    redis_client.zadd(category_key, {normalized_producto_id: parsed_score})

    cache_top = refresh_redis_top_cache(redis_client)
    stored_score = redis_client.zscore(TRENDING_GLOBAL_KEY, normalized_producto_id)
    stored_category_score = (
        redis_client.zscore(category_key, normalized_producto_id)
        if category_key
        else None
    )

    return operation_result(
        "Redis",
        "upsert_ranking_global_y_categoria",
        f"ZADD {TRENDING_GLOBAL_KEY} score producto_id; ZADD {TRENDING_CATEGORY_PREFIX}<categoria_id> score producto_id; SETEX {CACHE_TOP10_GLOBAL_KEY}",
        {
            "global_key": TRENDING_GLOBAL_KEY,
            "category_key": category_key,
            "producto_id": normalized_producto_id,
            "categoria_id": resolved_categoria_id,
            "score": parsed_score,
        },
        {
            "verified": (
                stored_score == parsed_score
                and stored_category_score == parsed_score
            ),
            "persisted": stored_score is not None,
            "read_back": {
                "producto_id": normalized_producto_id,
                "global_score": stored_score,
                "category_score": stored_category_score,
            },
        },
        {
            "category_source": category_source,
            "removed_from_other_categories": removed_from_other_categories,
            "cache_top10_global": cache_top,
        },
    )


def redis_delete_global_score(producto_id):
    normalized_producto_id = require_identifier(producto_id, "producto_id")
    redis_client = get_redis_client()
    removed = redis_client.zrem(TRENDING_GLOBAL_KEY, normalized_producto_id)
    removed_from_categories = remove_product_from_category_rankings(
        redis_client,
        normalized_producto_id,
    )
    cache_top = refresh_redis_top_cache(redis_client)
    stored_score = redis_client.zscore(TRENDING_GLOBAL_KEY, normalized_producto_id)
    remaining_category_hits = [
        key
        for key in redis_client.scan_iter(match=f"{TRENDING_CATEGORY_PREFIX}*")
        if redis_client.zscore(key, normalized_producto_id) is not None
    ]

    return operation_result(
        "Redis",
        "delete_ranking_global_y_categoria",
        f"ZREM {TRENDING_GLOBAL_KEY} producto_id; ZREM {TRENDING_CATEGORY_PREFIX}* producto_id; SETEX {CACHE_TOP10_GLOBAL_KEY}",
        {
            "key": TRENDING_GLOBAL_KEY,
            "producto_id": normalized_producto_id,
        },
        {
            "verified": stored_score is None and not remaining_category_hits,
            "deleted": stored_score is None and not remaining_category_hits,
            "read_back": {
                "producto_id": normalized_producto_id,
                "score": stored_score,
                "remaining_category_hits": remaining_category_hits,
            },
        },
        {
            "removed_global": removed,
            "removed_from_categories": removed_from_categories,
            "cache_top10_global": cache_top,
        },
    )


def neo4j_upsert_user_event(usuario_id, producto_id, tipo_evento):
    driver = None

    try:
        tipo_normalizado = normalize_event_type(tipo_evento, "tipo_evento")
        params = {
            "usuario_id": require_identifier(usuario_id, "usuario_id"),
            "producto_id": require_identifier(producto_id, "producto_id"),
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
    candidate = require_text(value, field_name).upper()
    normalized = EVENT_TYPE_ALIASES.get(candidate)

    if not normalized:
        raise ValueError(
            f"{field_name} debe ser uno de: " + ", ".join(TIPOS_INTERACCION)
        )

    return normalized


def neo4j_delete_user_event(usuario_id, producto_id, tipo_evento):
    driver = None

    try:
        tipo_normalizado = normalize_event_type(tipo_evento, "tipo_evento")
        params = {
            "usuario_id": require_identifier(usuario_id, "usuario_id"),
            "producto_id": require_identifier(producto_id, "producto_id"),
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
