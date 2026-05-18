import importlib


def run_optional_queries(step_name, module_path, function_name):
    """
    Ejecuta consultas demo si el módulo existe.
    Cada responsable de motor debe implementar sus propias queries.
    """
    try:
        module = importlib.import_module(module_path)
        function = getattr(module, function_name)
    except (ImportError, AttributeError):
        print(f"{step_name}: pendiente de implementación")
        return

    print(f"Ejecutando {step_name}...")
    function()


def run_all_queries():
    """
    Punto central para ejecutar consultas de demostración.

    Cada responsable debe implementar:
    - app.queries.mongo_queries.run_mongo_queries
    - app.queries.cassandra_queries.run_cassandra_queries
    - app.queries.redis_queries.run_redis_queries
    - app.queries.neo4j_queries.run_neo4j_queries
    """

    print("Iniciando consultas generales...")
    print("-" * 50)

    run_optional_queries(
        "consultas MongoDB",
        "app.queries.mongo_queries",
        "run_mongo_queries"
    )

    run_optional_queries(
        "consultas Cassandra",
        "app.queries.cassandra_queries",
        "run_cassandra_queries"
    )

    run_optional_queries(
        "consultas Redis",
        "app.queries.redis_queries",
        "run_redis_queries"
    )

    run_optional_queries(
        "consultas Neo4j",
        "app.queries.neo4j_queries",
        "run_neo4j_queries"
    )

    print("-" * 50)
    print("Consultas generales finalizadas.")