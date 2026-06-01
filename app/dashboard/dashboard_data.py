import importlib


def call_optional_dashboard_data(label, module_path, function_name, *args, **kwargs):
    """
    Intenta ejecutar una función de dashboard data.

    Si la función todavía no existe o falla, devuelve una respuesta controlada
    para que el dashboard no se rompa.
    """

    try:
        module = importlib.import_module(module_path)
        function = getattr(module, function_name)
        return function(*args, **kwargs)

    except (ImportError, AttributeError):
        return {
            "status": "pending",
            "message": f"{label}: función pendiente de implementación"
        }

    except Exception as error:
        return {
            "status": "error",
            "message": f"{label}: error al obtener datos",
            "error": str(error)
        }


def build_category_name_map(mongo_data):
    """
    Arma un diccionario categoria_id -> nombre usando MongoDB.

    MongoDB es la fuente documental de categorias, por eso el dashboard usa
    esta informacion para mostrar nombres legibles sobre datos de otros motores.
    """

    if mongo_data.get("status") != "ok":
        return {}

    return {
        row["categoria_id"]: row["categoria"]
        for row in mongo_data.get("productos_por_categoria", [])
        if row.get("categoria_id") and row.get("categoria")
    }


def add_category_names(rows, category_names):
    """
    Agrega categoria_nombre a filas que ya traen categoria_id.

    Si MongoDB no tiene el nombre disponible, se deja el ID como fallback para
    no romper la tabla del dashboard.
    """

    enriched_rows = []

    for row in rows:
        enriched_row = dict(row)
        categoria_id = enriched_row.get("categoria_id")

        if categoria_id:
            enriched_row["categoria_nombre"] = category_names.get(
                categoria_id,
                categoria_id,
            )

        enriched_rows.append(enriched_row)

    return enriched_rows


def enrich_dashboard_category_names(data):
    """
    Enriquecer la salida agregada sin cambiar los modelos fisicos.

    Cassandra sigue guardando categoria_id, pero el dashboard puede mostrar el
    nombre tomando el catalogo maestro desde MongoDB.
    """

    category_names = build_category_name_map(data.get("mongo", {}))

    for key in ["productos_mayor_precio", "stock_bajo"]:
        data["mongo"][key] = add_category_names(
            data.get("mongo", {}).get(key, []),
            category_names,
        )

    for key in [
        "top_tendencias_categoria_fecha",
        "top_tendencias_resumen_diario",
        "resumen_diario_sample",
    ]:
        data["cassandra"][key] = add_category_names(
            data.get("cassandra", {}).get(key, []),
            category_names,
        )

    return data


def get_dashboard_data(cassandra_fecha=None):
    """
    Junta las salidas de dashboard de las cuatro bases.

    cassandra_fecha permite pedir el resumen diario para una fecha elegida
    desde el frontend.

    Cada módulo de queries debe implementar su función correspondiente:
    - get_mongo_dashboard_data()
    - get_cassandra_dashboard_data()
    - get_redis_dashboard_data()
    - get_neo4j_dashboard_data()
    """

    data = {
        "mongo": call_optional_dashboard_data(
            "MongoDB",
            "app.queries.mongo_queries",
            "get_mongo_dashboard_data"
        ),
        "cassandra": call_optional_dashboard_data(
            "Cassandra",
            "app.queries.cassandra_queries",
            "get_cassandra_dashboard_data",
            fecha=cassandra_fecha,
        ),
        "redis": call_optional_dashboard_data(
            "Redis",
            "app.queries.redis_queries",
            "get_redis_dashboard_data"
        ),
        "neo4j": call_optional_dashboard_data(
            "Neo4j",
            "app.queries.neo4j_queries",
            "get_neo4j_dashboard_data"
        ),
    }

    return enrich_dashboard_category_names(data)
