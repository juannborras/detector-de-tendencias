import importlib

from app.config import LOAD_MODE
from app.generators.data_generator import generate_dataset, print_dataset_summary


def run_optional_loader(step_name, module_path, function_name, dataset):
    """
    Ejecuta un loader si existe.
    Cada loader recibe el mismo dataset común para mantener coherencia entre bases.
    """
    try:
        module = importlib.import_module(module_path)
        function = getattr(module, function_name)
    except (ImportError, AttributeError):
        print(f"{step_name}: pendiente de implementación")
        return

    print(f"Ejecutando {step_name}...")
    function(dataset)


def load_all():
    """
    Punto central de carga de datos.

    Genera una única vez el dataset común y lo pasa a todos los loaders.
    Esto asegura que MongoDB, Cassandra, Redis y Neo4j trabajen con los mismos IDs.
    """

    print("Iniciando carga general de datos...")
    print("-" * 50)
    print(f"Modo de carga: {LOAD_MODE}")

    dataset = generate_dataset()
    print_dataset_summary(dataset)

    print("-" * 50)

    run_optional_loader(
        "carga MongoDB",
        "app.loaders.mongo_loader",
        "load_mongo",
        dataset
    )

    run_optional_loader(
        "carga Cassandra",
        "app.loaders.cassandra_loader",
        "load_cassandra",
        dataset
    )

    run_optional_loader(
        "carga Redis",
        "app.loaders.redis_loader",
        "load_redis",
        dataset
    )

    run_optional_loader(
        "carga Neo4j",
        "app.loaders.neo4j_loader",
        "load_neo4j",
        dataset
    )

    print("-" * 50)
    print("Carga general finalizada.")