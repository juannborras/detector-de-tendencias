import importlib


def call_optional_dashboard_data(label, module_path, function_name):
    """
    Intenta ejecutar una función de dashboard data.

    Si la función todavía no existe o falla, devuelve una respuesta controlada
    para que el dashboard no se rompa.
    """

    try:
        module = importlib.import_module(module_path)
        function = getattr(module, function_name)
        return function()

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


def get_dashboard_data():
    """
    Junta las salidas de dashboard de las cuatro bases.

    Cada módulo de queries debe implementar su función correspondiente:
    - get_mongo_dashboard_data()
    - get_cassandra_dashboard_data()
    - get_redis_dashboard_data()
    - get_neo4j_dashboard_data()
    """

    return {
        "mongo": call_optional_dashboard_data(
            "MongoDB",
            "app.queries.mongo_queries",
            "get_mongo_dashboard_data"
        ),
        "cassandra": call_optional_dashboard_data(
            "Cassandra",
            "app.queries.cassandra_queries",
            "get_cassandra_dashboard_data"
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