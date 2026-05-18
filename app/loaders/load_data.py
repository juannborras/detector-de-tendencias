import importlib


def run_optional_loader(step_name, module_path, function_name):
    """
    Ejecuta un loader si existe.
    Sirve para que cada responsable de motor agregue su módulo
    sin romper la integración general.
    """
    try:
        module = importlib.import_module(module_path)
        function = getattr(module, function_name)
    except (ImportError, AttributeError):
        print(f"{step_name}: pendiente de implementación")
        return

    print(f"Ejecutando {step_name}...")
    function()


def load_all():
    """
    Punto central de carga de datos.

    Cada responsable debe implementar su loader específico:
    - app.loaders.mongo_loader.load_mongo
    - app.loaders.cassandra_loader.load_cassandra
    - app.loaders.redis_loader.load_redis
    - app.loaders.neo4j_loader.load_neo4j
    """

    print("Iniciando carga general de datos...")
    print("-" * 50)

    run_optional_loader(
        "carga MongoDB",
        "app.loaders.mongo_loader",
        "load_mongo"
    )

    run_optional_loader(
        "carga Cassandra",
        "app.loaders.cassandra_loader",
        "load_cassandra"
    )

    run_optional_loader(
        "carga Redis",
        "app.loaders.redis_loader",
        "load_redis"
    )

    run_optional_loader(
        "carga Neo4j",
        "app.loaders.neo4j_loader",
        "load_neo4j"
    )

    print("-" * 50)
    print("Carga general finalizada.")